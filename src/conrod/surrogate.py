import json
import hashlib
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from .schemas import BOUNDS, GEOMETRY_VERSION
from .dataset import load_verified

FEATURES = list(BOUNDS) + [
    "force_n",
    "compression",
    "youngs_modulus_mpa",
    "poissons_ratio",
    "density_kg_per_mm3",
    "yield_strength_mpa",
]
TARGETS = ["max_von_mises_mpa", "max_displacement_mm"]


def features(g, m, load):
    d = {
        **g.to_dict(),
        **m.to_dict(),
        "force_n": load.force_n,
        "compression": float(load.kind == "compression"),
    }
    return np.array([d[k] for k in FEATURES], dtype=float)


def metrics(y, p):
    return {
        k: dict(
            MAE=float(mean_absolute_error(y[:, i], p[:, i])),
            RMSE=float(np.sqrt(mean_squared_error(y[:, i], p[:, i]))),
            R2=float(r2_score(y[:, i], p[:, i])),
        )
        for i, k in enumerate(TARGETS)
    }


def geometry_groups(rows, tolerance=0.01):
    # Union near-neighbours, including designs on opposite sides of rounding bins.
    from scipy.spatial import cKDTree

    names = list(BOUNDS)
    spans = np.array([BOUNDS[k][1] - BOUNDS[k][0] for k in names])
    points = np.array([[r["geometry"][k] for k in names] for r in rows]) / spans
    parents = list(range(len(rows)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for i, j in cKDTree(points).query_pairs(tolerance, p=np.inf):
        parents[find(j)] = find(i)
    return np.array([find(i) for i in range(len(rows))])


def train(dataset, output, seed=42):
    from .schemas import Geometry, Material, LoadCase

    rows = load_verified(dataset)
    if len(rows) < 24:
        raise ValueError(
            "At least 24 successful analyses required for exploratory comparison"
        )
    if len({json.dumps(r["mesh"], sort_keys=True) for r in rows}) != 1 or any(
        r["geometry_version"] != GEOMETRY_VERSION for r in rows
    ):
        raise ValueError("Incompatible mesh fidelity or geometry versions")
    X = np.array(
        [
            features(
                Geometry(**r["geometry"]),
                Material(**r["material"]),
                LoadCase(**r["load"]),
            )
            for r in rows
        ]
    )
    y = np.array([[r[k] for k in TARGETS] for r in rows])
    # Connected groups of geometries within 1% of each supported dimensional span.
    groups = geometry_groups(rows)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    rest, test = next(splitter.split(X, y, groups))
    a, b = next(
        GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1).split(
            X[rest], y[rest], groups[rest]
        )
    )
    train_idx, val = rest[a], rest[b]
    models = {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=150, min_samples_leaf=2, random_state=seed, n_jobs=2
        ),
        "mlp": make_pipeline(
            StandardScaler(),
            MLPRegressor(
                hidden_layer_sizes=(32, 16),
                solver="lbfgs",
                alpha=0.1,
                max_iter=1500,
                random_state=seed,
            ),
        ),
    }
    scores = {}
    fitted = {}
    scales = np.std(y[train_idx], axis=0)
    for name, base in models.items():
        model = TransformedTargetRegressor(
            regressor=base, transformer=StandardScaler()
        ).fit(X[train_idx], y[train_idx])
        pred = model.predict(X[val])
        scores[name] = dict(
            training=metrics(y[train_idx], model.predict(X[train_idx])),
            validation=metrics(y[val], pred),
            selection_score=float(np.mean(np.abs(y[val] - pred) / scales)),
        )
        fitted[name] = model
    winner = min(scores, key=lambda k: scores[k]["selection_score"])
    model = fitted[winner]
    # Keep validation disjoint; never refit on validation before deriving the observed residual margin.
    margin = np.max(np.maximum(y[val] - model.predict(X[val]), 0), axis=0)
    test_pred = model.predict(X[test])
    test_metrics = metrics(y[test], test_pred)
    for name, model_i in fitted.items():
        scores[name]["test"] = metrics(y[test], model_i.predict(X[test]))
    boundary = np.array(
        [
            1.4 <= rows[i]["factor_of_safety"] <= 2.2
            or 0.28 <= rows[i]["max_displacement_mm"] <= 0.42
            for i in test
        ]
    )
    report = dict(
        model_version="fea-1",
        software_versions=dict(
            numpy=np.__version__, sklearn=__import__("sklearn").__version__
        ),
        selected_model=winner,
        dataset_sha256=hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        supported_materials=list(
            {json.dumps(rows[i]["material"], sort_keys=True) for i in train_idx}
        ),
        constraint_region="FoS in [1.4,2.2] or displacement in [0.28,0.42] mm",
        sample_count=len(rows),
        split_counts=dict(train=len(train_idx), validation=len(val), test=len(test)),
        groups_disjoint=not (
            set(groups[train_idx]) & set(groups[val])
            or set(groups[train_idx]) & set(groups[test])
            or set(groups[val]) & set(groups[test])
        ),
        comparisons=scores,
        held_out_metrics=test_metrics,
        near_constraint_test_count=int(boundary.sum()),
        near_constraint_metrics=metrics(y[test][boundary], test_pred[boundary])
        if boundary.sum() > 1
        else None,
        residual_margin=margin.tolist(),
        margin_claim="Observed validation maximum underprediction; not calibrated confidence",
        seed=seed,
        training_configuration=dict(
            ridge_alpha=1.0,
            trees=150,
            tree_min_samples_leaf=2,
            mlp_hidden=[32, 16],
            mlp_solver="lbfgs",
            mlp_alpha=0.1,
            mlp_max_iter=1500,
            scaling="StandardScaler X for Ridge/MLP; StandardScaler y for all",
        ),
        supported_min=X[train_idx].min(axis=0).tolist(),
        supported_max=X[train_idx].max(axis=0).tolist(),
        features=FEATURES,
        targets=TARGETS,
        geometry_version=GEOMETRY_VERSION,
        split_ids={
            name: [rows[i]["sample_id"] for i in idx]
            for name, idx in [("train", train_idx), ("validation", val), ("test", test)]
        },
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(model=model, metadata=report), output)
    output.with_suffix(".json").write_text(json.dumps(report, indent=2))
    predictions = pd.DataFrame(
        {f"{k}_actual": y[test][:, i] for i, k in enumerate(TARGETS)}
    )
    for i, k in enumerate(TARGETS):
        predictions[f"{k}_predicted"] = test_pred[:, i]
        predictions[f"{k}_residual"] = y[test][:, i] - test_pred[:, i]
    predictions.to_csv(output.with_suffix(".test.csv"), index=False)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for i, k in enumerate(TARGETS):
        axes[0, i].scatter(y[test][:, i], test_pred[:, i])
        limits = [min(y[test][:, i]), max(y[test][:, i])]
        axes[0, i].plot(limits, limits, "k--")
        axes[0, i].set(xlabel="FEA", ylabel="Prediction", title=k)
        axes[1, i].hist(y[test][:, i] - test_pred[:, i], bins=10)
        axes[1, i].set(xlabel="FEA minus prediction", ylabel="Count")
    fig.tight_layout()
    fig.savefig(output.with_suffix(".evaluation.png"))
    plt.close(fig)
    return report


class Surrogate:
    def __init__(self, path):
        # Caller must supply a trusted local artifact. Pickle is not a safe interchange format.
        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.metadata = bundle["metadata"]
        if (
            self.metadata["features"] != FEATURES
            or self.metadata["geometry_version"] != GEOMETRY_VERSION
        ):
            raise ValueError("Incompatible model schema")

    def predict(self, g, m, load, allow_extrapolation=False):
        g.validate()
        m.validate()
        load.validate()
        x = features(g, m, load)
        if (
            self.metadata.get("supported_materials")
            and json.dumps(m.to_dict(), sort_keys=True)
            not in self.metadata["supported_materials"]
        ):
            raise ValueError("Material combination was not represented in training")
        lo = np.array(self.metadata["supported_min"])
        hi = np.array(self.metadata["supported_max"])
        outside = bool(np.any(x < lo - 1e-8) or np.any(x > hi + 1e-8))
        if outside and not allow_extrapolation:
            raise ValueError("Outside demonstrated training ranges")
        p = np.asarray(self.model.predict(x[None, :]))[0]
        if not np.isfinite(p).all() or np.any(p <= 0):
            raise ValueError("Nonphysical surrogate prediction")
        return dict(
            zip(TARGETS, map(float, p))
        )  # Preserve full precision for differentiation.
