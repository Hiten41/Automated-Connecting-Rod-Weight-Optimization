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
    "length_cc", "big_end_id", "small_end_id", "ring_thickness", "shank_width",
    "beam_thickness", "flange_thickness_mm", "web_thickness_mm",
    "transition_radius_mm", "taper_big_width_mm", "taper_mid_width_mm",
    "taper_small_width_mm", "rib_height_mm", "rib_length_mm", "pocket_length_mm",
    "pocket_width_mm", "cad_mass_g", "load_force_n",
]
CATEGORICAL = ["geometry_family", "load_case"]


def make_model(model):
    prep = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ])
    return Pipeline([("prep", prep), ("regressor", model)])


def metrics(y, p):
    return {
        "n": int(len(y)),
        "mae_mpa": float(mean_absolute_error(y, p)),
        "rmse_mpa": float(np.sqrt(mean_squared_error(y, p))),
        "r2": float(r2_score(y, p)),
    }


def main():
    rows = [json.loads(line) for line in (DATA / "fea-dataset.jsonl").read_text().splitlines() if line]
    frame = pd.DataFrame(rows)
    features = []
    for _, row in frame.iterrows():
        features.append({**row["geometry_parameters"],
                         "geometry_family": row["geometry_family"],
                         "load_case": row["load_case"],
                         "cad_mass_g": row["cad_mass_g"],
                         "load_force_n": row["load_force_n"]})
    X = pd.DataFrame(features)
    X = X.reindex(columns=NUMERIC + CATEGORICAL)
    y = frame["peak_unaveraged_ip_von_mises_mpa"].to_numpy(dtype=float)
    groups = (frame["study"].astype(str) + "|" + frame["candidate_id"].astype(str)).to_numpy()
    coarse_mask = frame["mesh_fidelity"].eq("6mm_coarse").to_numpy()
    models = {
        "Ridge": Ridge(alpha=10.0),
        "Extra Trees": ExtraTreesRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=1),
        "MLP": MLPRegressor(hidden_layer_sizes=(48, 24), alpha=1.0, max_iter=1500, random_state=42),
    }
    coarse_X, coarse_y, coarse_groups = X.loc[coarse_mask].reset_index(drop=True), y[coarse_mask], groups[coarse_mask]
    splitter = GroupKFold(n_splits=5)
    grouped_results = {}
    grouped_predictions = {}
    for name, regressor in models.items():
        pred = np.full(len(coarse_y), np.nan)
        for train, test in splitter.split(coarse_X, coarse_y, coarse_groups):
            estimator = make_model(regressor)
            estimator.fit(coarse_X.iloc[train], coarse_y[train])
            pred[test] = estimator.predict(coarse_X.iloc[test])
        grouped_results[name] = metrics(coarse_y, pred)
        grouped_predictions[name] = pred

    fine_mask = frame["mesh_fidelity"].str.startswith("local_").to_numpy()
    fine_rows = frame.loc[fine_mask].copy()
    final_level_by_id = {"P4-0065": "local_0.5mm"}
    fine_rows = fine_rows[
        fine_rows.apply(lambda r: r["mesh_fidelity"] == final_level_by_id.get(r["candidate_id"], "local_0.75mm"), axis=1)
    ].reset_index(drop=True)
    fine_groups = set(fine_rows["geometry_hash"])
    train_rows = frame[coarse_mask & ~frame["geometry_hash"].isin(fine_groups).to_numpy()].reset_index(drop=True)
    train_features = []
    for _, row in train_rows.iterrows():
        train_features.append({**row["geometry_parameters"],
                               "geometry_family": row["geometry_family"],
                               "load_case": row["load_case"],
                               "cad_mass_g": row["cad_mass_g"],
                               "load_force_n": row["load_force_n"]})
    fine_features = []
    for _, row in fine_rows.iterrows():
        fine_features.append({**row["geometry_parameters"],
                              "geometry_family": row["geometry_family"],
                              "load_case": row["load_case"],
                              "cad_mass_g": row["cad_mass_g"],
                              "load_force_n": row["load_force_n"]})
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

    output = {
        "dataset": {
            "rows": int(len(frame)),
            "coarse_rows": int(coarse_mask.sum()),
            "refined_rows": int(fine_mask.sum()),
            "coarse_geometry_groups": int(len(set(coarse_groups))),
            "fine_holdout_geometry_groups": int(len(fine_groups)),
            "fine_holdout_rows": int(len(fine_rows)),
            "features": NUMERIC + CATEGORICAL,
        },
        "coarse_grouped_5fold_oof": grouped_results,
        "coarse_trained_fine_geometry_holdout": fine_results,
        "authority_note": "Research diagnostics only. Small fine-mesh geometry sample and fidelity shift prohibit surrogate constraint enforcement.",
    }
    (DATA / "ml-evaluation.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, truth, preds, title in (
        (axes[0], coarse_y, grouped_predictions, "Coarse grouped 5-fold holdout"),
        (axes[1], y_fine, fine_predictions, "Fine-mesh geometry holdout"),
    ):
        for name, pred in preds.items():
            ax.scatter(truth, pred, s=24, alpha=.7, label=name)
        limits = [0, max(float(np.max(truth)), max(float(np.max(p)) for p in preds.values())) * 1.05]
        ax.plot(limits, limits, "k--", linewidth=1)
        ax.axvline(394.444444, color="#b42318", linestyle=":", linewidth=1)
        ax.axhline(394.444444, color="#b42318", linestyle=":", linewidth=1)
        ax.set_xlim(limits)
        ax.set_ylim(limits)
        ax.set_title(title)
        ax.set_xlabel("Actual peak stress (MPa)")
        ax.set_ylabel("Predicted peak stress (MPa)")
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8)
    fig.suptitle("Phase 4 ML diagnostics · grouped by geometry · not used for acceptance")
    fig.tight_layout()
    fig.savefig(FIG / "phase4-ml-model-comparison.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
