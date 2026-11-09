"""Measured feasibility plots and explicit incomplete-study status."""

import json

import pandas as pd
import plotly.express as px
from scipy.stats import spearmanr

from conrod.fea import ROOT


def run():
    root = ROOT / "data/phase3/feasibility"
    rows = json.loads((root / "candidates.json").read_text(encoding="utf-8"))
    flat = []
    for r in rows:
        d = dict(
            index=r["index"],
            status=r["assessment"]["status"],
            **r["parameters"],
            mass_g=r.get("mass_kg", 0) * 1000,
        )
        for result in r.get("results", []):
            if result["status"] == "FEA_SUCCESS":
                d[result["load"]["kind"] + "_stress_mpa"] = result["max_von_mises_mpa"]
                d[result["load"]["kind"] + "_displacement_mm"] = result[
                    "max_displacement_mm"
                ]
        d["constraint_margin_mpa"] = 710 / 1.8 - max(
            d.get("compression_stress_mpa", float("nan")),
            d.get("tension_stress_mpa", float("nan")),
        )
        flat.append(d)
    frame = pd.DataFrame(flat)
    frame.to_csv(root / "feasibility.csv", index=False)
    counts = frame.status.value_counts().to_dict()
    valid = frame.dropna(subset=["compression_stress_mpa", "tension_stress_mpa"])
    sensitivity = {}
    parameter_names = [
        "ring_thickness",
        "shank_width",
        "beam_thickness",
        "pocket_depth",
        "flange_thickness",
        "transition_radius_mm",
    ]
    for response in [
        "compression_stress_mpa",
        "tension_stress_mpa",
        "mass_g",
        "compression_displacement_mm",
        "tension_displacement_mm",
    ]:
        comparisons = []
        for parameter in parameter_names:
            sample = valid[[parameter, response]].dropna()
            rho, p_value = spearmanr(sample[parameter], sample[response])
            comparisons.append(
                dict(
                    parameter=parameter,
                    spearman_rho=float(rho),
                    unadjusted_p_value=float(p_value),
                    sample_count=len(sample),
                )
            )
        sensitivity[response] = sorted(
            comparisons, key=lambda row: abs(row["spearman_rho"]), reverse=True
        )
    sensitivity_record = {
        "method": "unadjusted Spearman rank association across valid Latin-hypercube cases",
        "sample_count": len(valid),
        "interpretation": "Exploratory association only; geometry variables co-vary and this is not a causal or global sensitivity analysis.",
        "responses": sensitivity,
    }
    (root / "sensitivity.json").write_text(
        json.dumps(sensitivity_record, indent=2), encoding="utf-8"
    )

    refined_path = ROOT / "data/phase3/near-boundary/results.json"
    refined = (
        json.loads(refined_path.read_text(encoding="utf-8"))
        if refined_path.exists()
        else []
    )
    refined_summary = []
    for candidate in refined:
        successful = [
            result
            for result in candidate["results"]
            if result.get("status") == "FEA_SUCCESS"
        ]
        refined_summary.append(
            {
                "candidate_id": candidate["candidate_id"],
                "status": candidate["status"],
                "loads_completed": len(successful),
                "stress_mpa": {
                    result["load"]["kind"]: result["max_von_mises_mpa"]
                    for result in successful
                },
                "displacement_mm": {
                    result["load"]["kind"]: result["max_displacement_mm"]
                    for result in successful
                },
            }
        )
    report = dict(
        attempted_geometries=len(rows),
        planned_geometries=40,
        counts=counts,
        actual_fea_geometries=len(valid),
        coarse_screen_passes=int((valid.constraint_margin_mpa >= 0).sum()),
        feasibility_conclusion="INCONCLUSIVE: NO FEASIBLE CANDIDATE FOUND IN 40 SAMPLED GEOMETRIES",
        qualification="40 actual CAD/LHS geometries screened using 6mm local FEA; the nearest sampled candidate was refined at 0.75mm and still failed tension. This does not prove the full bounded domain infeasible.",
        verified_feasible_candidates=0,
        refined_near_boundary=refined_summary,
        exploratory_variable_associations="sensitivity.json",
    )
    if counts.get("PROVISIONAL_SINGLE_MESH_PASS", 0):
        report["feasibility_conclusion"] = (
            "PROVISIONAL CANDIDATES REQUIRE REFINED VERIFICATION"
        )
    (root / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    out = ROOT / "evidence/phase3"
    out.mkdir(parents=True, exist_ok=True)
    for x, y in [
        ("mass_g", "tension_stress_mpa"),
        ("mass_g", "compression_stress_mpa"),
        ("mass_g", "tension_displacement_mm"),
        ("compression_stress_mpa", "tension_stress_mpa"),
        ("mass_g", "constraint_margin_mpa"),
    ]:
        if y not in frame:
            continue
        fig = px.scatter(
            frame,
            x=x,
            y=y,
            color="status",
            hover_data=["index"],
            title="Actual6mm FEA screening — not converged design acceptance",
        )
        fig.write_html(out / f"feasibility-{x}-{y}.html")
    for key in [
        "ring_thickness",
        "shank_width",
        "beam_thickness",
        "pocket_depth",
        "flange_thickness",
        "transition_radius_mm",
    ]:
        if "tension_stress_mpa" in frame:
            px.scatter(
                frame,
                x=key,
                y="tension_stress_mpa",
                color="status",
                hover_data=["index"],
            ).write_html(out / f"feasibility-{key}.html")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
