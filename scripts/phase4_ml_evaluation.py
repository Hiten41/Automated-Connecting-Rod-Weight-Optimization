"""Grouped coarse-FEA model comparison with a geometry-held-out fine test."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/phase4"
FIG = ROOT / "docs/phase4/final/figures"
NUMERIC = [
    "length_cc",
    "big_end_id",
    "small_end_id",
    "ring_thickness",
    "shank_width",
    "beam_thickness",
    "flange_thickness_mm",
    "web_thickness_mm",
    "transition_radius_mm",
    "taper_big_width_mm",
    "taper_mid_width_mm",
    "taper_small_width_mm",
    "rib_height_mm",
    "rib_length_mm",
    "pocket_length_mm",
    "pocket_width_mm",
    "cad_mass_g",
    "load_force_n",
]
CATEGORICAL = ["geometry_family", "load_case"]


def make_model(model):
    prep = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC,
            ),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL,
            ),
        ]
    )
    return Pipeline([("prep", prep), ("regressor", model)])


def metrics(y, p):
    return {
        "n": len(y),
        "mae_mpa": float(mean_absolute_error(y, p)),
        "rmse_mpa": float(np.sqrt(mean_squared_error(y, p))),
        "r2": float(r2_score(y, p)),
    }


def main():
    rows = [
        json.loads(line)
        for line in (DATA / "fea-dataset.jsonl").read_text().splitlines()
        if line
    ]
    frame = pd.DataFrame(rows)
    features = []
    for _, row in frame.iterrows():
        features.append(
            {
                **row["geometry_parameters"],
                "geometry_family": row["geometry_family"],
                "load_case": row["load_case"],
                "cad_mass_g": row["cad_mass_g"],
                "load_force_n": row["load_force_n"],
            }
        )
    X = pd.DataFrame(features)
    X = X.reindex(columns=NUMERIC + CATEGORICAL)
    y = frame["peak_unaveraged_ip_von_mises_mpa"].to_numpy(dtype=float)
    if (
        frame["geometry_hash"].isna().any()
        or frame["geometry_hash"].astype(str).str.len().eq(0).any()
    ):
        raise ValueError("Every Phase 4 ML row must have a canonical geometry_hash")
    coarse_mask = frame["mesh_fidelity"].eq("6mm_coarse").to_numpy()
    coarse_frame = frame.loc[coarse_mask].reset_index(drop=True)
    coarse_groups = coarse_frame["geometry_hash"].astype(str).to_numpy()
    for geometry_hash, rows_for_geometry in coarse_frame.groupby("geometry_hash"):
        parameter_records = {
            json.dumps(value, sort_keys=True)
            for value in rows_for_geometry["geometry_parameters"]
        }
        if len(parameter_records) > 1:
            raise ValueError(
                f"Geometry hash {geometry_hash} maps to multiple parameter records"
            )
    models = {
        "Ridge": Ridge(alpha=10.0),
        "Extra Trees": ExtraTreesRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=1
        ),
        "MLP": MLPRegressor(
            hidden_layer_sizes=(48, 24), alpha=1.0, max_iter=1500, random_state=42
        ),
    }
    coarse_X = X.loc[coarse_mask].reset_index(drop=True)
    coarse_y = y[coarse_mask]
    splitter = GroupKFold(n_splits=5)
    grouped_results = {}
    grouped_predictions = {}
    grouped_fold_ids = {}
    fold_audit = []
    for name, regressor in models.items():
        pred = np.full(len(coarse_y), np.nan)
        fold_ids = np.full(len(coarse_y), -1, dtype=int)
        for fold_id, (train, test) in enumerate(
            splitter.split(coarse_X, coarse_y, coarse_groups), start=1
        ):
            train_hashes = set(coarse_groups[train])
            test_hashes = set(coarse_groups[test])
            if not train_hashes.isdisjoint(test_hashes):
                raise AssertionError(
                    "Geometry hash leakage across coarse train/test fold"
                )
            estimator = make_model(regressor)
            estimator.fit(coarse_X.iloc[train], coarse_y[train])
            pred[test] = estimator.predict(coarse_X.iloc[test])
            fold_ids[test] = fold_id
            if name == next(iter(models)):
                fold_audit.append(
                    {
                        "fold_id": fold_id,
                        "train_geometry_groups": len(train_hashes),
                        "test_geometry_groups": len(test_hashes),
                        "train_geometry_hashes": sorted(train_hashes),
                        "test_geometry_hashes": sorted(test_hashes),
                        "geometry_hashes_disjoint": True,
                    }
                )
        if not np.isfinite(pred).all() or (fold_ids < 1).any():
            raise AssertionError(f"Incomplete out-of-fold predictions for {name}")
        grouped_results[name] = metrics(coarse_y, pred)
        grouped_predictions[name] = pred
        grouped_fold_ids[name] = fold_ids

    fine_mask = frame["mesh_fidelity"].str.startswith("local_").to_numpy()
    fine_rows = frame.loc[fine_mask].copy()
    final_level_by_id = {"P4-0065": "local_0.5mm"}
    fine_rows = fine_rows[
        fine_rows.apply(
            lambda r: (
                r["mesh_fidelity"]
                == final_level_by_id.get(r["candidate_id"], "local_0.75mm")
            ),
            axis=1,
        )
    ].reset_index(drop=True)
    fine_groups = set(fine_rows["geometry_hash"])
    train_rows = frame[
        coarse_mask & ~frame["geometry_hash"].isin(fine_groups).to_numpy()
    ].reset_index(drop=True)
    train_groups = set(train_rows["geometry_hash"])
    if not train_groups.isdisjoint(fine_groups):
        raise AssertionError("Fine geometry holdout leaked into coarse training data")
    train_features = []
    for _, row in train_rows.iterrows():
        train_features.append(
            {
                **row["geometry_parameters"],
                "geometry_family": row["geometry_family"],
                "load_case": row["load_case"],
                "cad_mass_g": row["cad_mass_g"],
                "load_force_n": row["load_force_n"],
            }
        )
    fine_features = []
    for _, row in fine_rows.iterrows():
        fine_features.append(
            {
                **row["geometry_parameters"],
                "geometry_family": row["geometry_family"],
                "load_case": row["load_case"],
                "cad_mass_g": row["cad_mass_g"],
                "load_force_n": row["load_force_n"],
            }
        )
    X_train = pd.DataFrame(train_features).reindex(columns=NUMERIC + CATEGORICAL)
    X_fine = pd.DataFrame(fine_features).reindex(columns=NUMERIC + CATEGORICAL)
    y_train = train_rows["peak_unaveraged_ip_von_mises_mpa"].to_numpy(dtype=float)
    y_fine = fine_rows["peak_unaveraged_ip_von_mises_mpa"].to_numpy(dtype=float)
    fine_results = {}
    fine_predictions = {}
    for name, regressor in models.items():
        estimator = make_model(regressor)
        estimator.fit(X_train, y_train)
        pred = estimator.predict(X_fine)
        fine_results[name] = metrics(y_fine, pred)
        fine_predictions[name] = pred

    prediction_rows = []
    for name, predictions in grouped_predictions.items():
        for index, prediction in enumerate(predictions):
            row = coarse_frame.iloc[index]
            actual = float(coarse_y[index])
            prediction_rows.append(
                {
                    "evaluation": "coarse_grouped_5fold_oof",
                    "model": name,
                    "candidate_id": row["candidate_id"],
                    "geometry_hash": row["geometry_hash"],
                    "load_case": row["load_case"],
                    "mesh_fidelity": row["mesh_fidelity"],
                    "actual_stress_mpa": actual,
                    "predicted_stress_mpa": float(prediction),
                    "residual_mpa": actual - float(prediction),
                    "fold_id": int(grouped_fold_ids[name][index]),
                }
            )
    for name, predictions in fine_predictions.items():
        for index, prediction in enumerate(predictions):
            row = fine_rows.iloc[index]
            actual = float(y_fine[index])
            prediction_rows.append(
                {
                    "evaluation": "coarse_trained_fine_geometry_holdout",
                    "model": name,
                    "candidate_id": row["candidate_id"],
                    "geometry_hash": row["geometry_hash"],
                    "load_case": row["load_case"],
                    "mesh_fidelity": row["mesh_fidelity"],
                    "actual_stress_mpa": actual,
                    "predicted_stress_mpa": float(prediction),
                    "residual_mpa": actual - float(prediction),
                    "fold_id": None,
                }
            )

    output = {
        "dataset": {
            "rows": len(frame),
            "coarse_rows": int(coarse_mask.sum()),
            "refined_rows": int(fine_mask.sum()),
            "coarse_geometry_groups": len(set(coarse_groups)),
            "fine_holdout_geometry_groups": len(fine_groups),
            "fine_holdout_rows": len(fine_rows),
            "grouping_key": "geometry_hash",
            "coarse_fold_count": 5,
            "coarse_geometry_groups_disjoint": True,
            "fine_holdout_disjoint_from_coarse_training": True,
            "fine_holdout_geometry_hashes": sorted(fine_groups),
            "fine_training_geometry_hashes": sorted(train_groups),
            "features": NUMERIC + CATEGORICAL,
        },
        "coarse_grouped_fold_audit": fold_audit,
        "coarse_grouped_5fold_oof": grouped_results,
        "coarse_trained_fine_geometry_holdout": fine_results,
        "row_level_predictions": prediction_rows,
        "authority_note": "Research diagnostics only. Small fine-mesh geometry sample and fidelity shift prohibit surrogate constraint enforcement.",
    }
    (DATA / "ml-evaluation.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )

    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, truth, preds, title in (
        (axes[0], coarse_y, grouped_predictions, "Coarse grouped 5-fold holdout"),
        (axes[1], y_fine, fine_predictions, "Fine-mesh geometry holdout"),
    ):
        for name, pred in preds.items():
            ax.scatter(truth, pred, s=24, alpha=0.7, label=name)
        limits = [
            0,
            max(float(np.max(truth)), max(float(np.max(p)) for p in preds.values()))
            * 1.05,
        ]
        ax.plot(limits, limits, "k--", linewidth=1)
        ax.axvline(394.444444, color="#b42318", linestyle=":", linewidth=1)
        ax.axhline(394.444444, color="#b42318", linestyle=":", linewidth=1)
        ax.set_xlim(limits)
        ax.set_ylim(limits)
        ax.set_title(title)
        ax.set_xlabel("Actual peak stress (MPa)")
        ax.set_ylabel("Predicted peak stress (MPa)")
        ax.grid(alpha=0.2)
    axes[1].legend(fontsize=8)
    fig.suptitle(
        "Phase 4 ML diagnostics · grouped by geometry · not used for acceptance"
    )
    fig.tight_layout()
    fig.savefig(FIG / "phase4-ml-model-comparison.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
