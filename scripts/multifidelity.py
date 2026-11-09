"""Small paired-fidelity investigation with held-out geometry groups."""

import json
import hashlib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from conrod.fea import ROOT
from conrod.schemas import Geometry, Material, LoadCase, MeshSettings
from conrod.surrogate import features, metrics, TARGETS, geometry_groups
from conrod.dataset import load_verified
from phase2_experiments import run_case


def run():
    source = ROOT / "data/phase2/initial36/verified.jsonl"
    if not source.exists():
        source = ROOT / "data/phase2/coarse/verified.jsonl"
    rows = load_verified(source)
    groups = geometry_groups(rows)
    unique = np.unique(groups)
    chosen = unique[np.linspace(0, len(unique) - 1, 4, dtype=int)]
    fine = []
    indices = []
    for i, r in enumerate(rows):
        if groups[i] not in chosen:
            continue
        out = ROOT / "data/phase2/fine/cases" / r["sample_id"]
        f = run_case(
            Geometry(**r["geometry"]),
            Material(**r["material"]),
            LoadCase(**r["load"]),
            MeshSettings(4),
            out,
        )
        if f["status"] == "FEA_SUCCESS":
            fine.append(f)
            indices.append(i)
    out = ROOT / "data/phase2"
    (out / "fine").mkdir(exist_ok=True)
    (out / "fine/verified.jsonl").write_text(
        "".join(json.dumps(f) + "\n" for f in fine)
    )
    if len(fine) < 8:
        report = dict(
            status="INSUFFICIENT_PAIRED_DATA", successful_fine_cases=len(fine)
        )
    else:
        test_groups = set(chosen[-2:])
        coarse_train = [i for i in range(len(rows)) if groups[i] not in test_groups]
        fine_train = [j for j, i in enumerate(indices) if groups[i] not in test_groups]
        fine_test = [j for j, i in enumerate(indices) if groups[i] in test_groups]
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
        fy = np.array([[r[k] for k in TARGETS] for r in fine])
        fx = X[indices]

        def model():
            return TransformedTargetRegressor(
                regressor=make_pipeline(StandardScaler(), Ridge(alpha=1)),
                transformer=StandardScaler(),
            )

        coarse = model().fit(X[coarse_train], y[coarse_train])
        base = coarse.predict(fx)
        correction = model().fit(fx[fine_train], (fy - base)[fine_train])
        corrected = base + correction.predict(fx)
        raw_metrics = metrics(fy[fine_test], base[fine_test])
        corrected_metrics = metrics(fy[fine_test], corrected[fine_test])
        discrepancy = fy - y[indices]
        report = dict(
            status="EXPLORATORY_SMALL_SAMPLE",
            coarse_mesh_mm=8,
            fine_mesh_mm=4,
            coarse_train_cases=len(coarse_train),
            fine_train_cases=len(fine_train),
            held_out_fine_cases=len(fine_test),
            held_out_geometry_groups=[int(g) for g in test_groups],
            geometry_leakage=False,
            coarse_prediction_on_fine=raw_metrics,
            additive_ridge_correction_on_fine=corrected_metrics,
            mean_fine_minus_coarse=dict(
                zip(TARGETS, discrepancy.mean(axis=0).tolist())
            ),
            selected_for_optimization=False,
            limitation="Two held-out geometry groups only. 4mm is finer than 8mm, not independently converged. Correction is not promoted from this small investigation.",
        )
    report["coarse_source"] = source.relative_to(ROOT).as_posix()
    report["coarse_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    (out / "multifidelity.json").write_text(json.dumps(report, indent=2))
    print(report, flush=True)


if __name__ == "__main__":
    run()
