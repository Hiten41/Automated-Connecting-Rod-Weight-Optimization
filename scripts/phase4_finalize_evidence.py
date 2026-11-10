"""Consolidate compact, reproducible Phase 4 solver and design evidence."""

import json
from pathlib import Path

from conrod.design_exploration import normalized_constraint_margins
from conrod.phase4 import Phase4Constraints, assess_candidate


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = ROOT / "data/phase4/phase4-evidence.json"
REFINED_IDS = ("P4-0055", "P4-0026", "P4-0059", "P4-0016", "P4-0060", "P4-0065")
LEVELS_BY_ID = {
    candidate_id: ("1.25", "0.75")
    for candidate_id in REFINED_IDS
    if candidate_id != "P4-0065"
}
LEVELS_BY_ID["P4-0065"] = ("1.25", "0.75", "0.5")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    design_root = RUNS / "phase4-design-space"
    manifest = load_json(design_root / "manifest.json")
    lhs_root = RUNS / "phase4-design-space-lhs"
    lhs_manifest = load_json(lhs_root / "manifest.json")
    random_designs = {row["candidate_id"]: row for row in manifest}
    lhs_designs = {row["candidate_id"]: row for row in lhs_manifest}
    coarse_random = load_json(design_root / "fea/screen.json")
    coarse_lhs = load_json(lhs_root / "fea/screen.json")
    coarse = coarse_random + coarse_lhs
    phase3_root = ROOT.parent / "phase3-rod"
    phase3_comp = load_json(phase3_root / "runs/phase3-refinement/0.35-compression/result.json")
    phase3_tension = load_json(phase3_root / "runs/phase3-refinement/0.35-tension/result.json")

    rows = []
    constraints = Phase4Constraints()
    for candidate_id in REFINED_IDS:
        candidate = lhs_designs[candidate_id] if candidate_id == "P4-0065" else random_designs[candidate_id]
        levels = LEVELS_BY_ID[candidate_id]
        mesh_levels = {}
        results_by_level = {}
        for level in levels:
            case_results = {}
            for kind in ("compression", "tension"):
                path = RUNS / "phase4-refined" / candidate_id / f"local-{level}mm" / kind / "result.json"
                case_results[kind] = load_json(path)
            results_by_level[level] = case_results
            mesh_levels[level] = {
                kind: {
                    "status": result.get("status"),
                    "peak_unaveraged_ip_von_mises_mpa": result.get("max_von_mises_mpa"),
                    "max_displacement_mm": result.get("max_displacement_mm"),
                    "factor_of_safety_710_mpa": result.get("factor_of_safety"),
                    "nodes": result.get("node_count"),
                    "elements": result.get("element_count"),
                    "runtime_s": result.get("runtime_s"),
                    "mesh_quality": result.get("mesh_quality"),
                    "hotspot": result.get("hotspot"),
                    "boundary_conditions": result.get("boundary_conditions"),
                    "fields_path": result.get("fields_path"),
                    "output_dir": result.get("output_dir"),
                }
                for kind, result in case_results.items()
            }
        deltas = {}
        for prior, current in zip(levels, levels[1:]):
            pair_name = f"{prior}_to_{current}"
            deltas[pair_name] = {}
            for kind in ("compression", "tension"):
                coarser = results_by_level[prior][kind]
                finer = results_by_level[current][kind]
                deltas[pair_name][kind] = {
                    field: 100.0 * abs(finer[field] - coarser[field]) / abs(coarser[field])
                    for field in ("max_von_mises_mpa", "max_displacement_mm")
                }
        last_pair = f"{levels[-2]}_to_{levels[-1]}"
        max_stress_delta = max(
            deltas[last_pair][kind]["max_von_mises_mpa"] for kind in ("compression", "tension")
        )
        stress_trend_pass = max_stress_delta < 5.0
        complete_two_levels = all(
            results_by_level[level][kind].get("status") == "FEA_SUCCESS"
            for level in levels for kind in ("compression", "tension")
        )
        independent_refined = complete_two_levels and stress_trend_pass
        buckling_path = RUNS / "phase4-refined" / candidate_id / f"local-{levels[-1]}mm/buckling/buckling.json"
        buckling = load_json(buckling_path) if buckling_path.exists() else None
        fine = results_by_level["0.75"]
        assessment = assess_candidate(
            fine,
            buckling_factor=(buckling or {}).get("lowest_positive_factor"),
            independent_refined=independent_refined,
            constraints=constraints,
        )
        assessment["mesh_stress_trend_max_percent"] = max_stress_delta
        if not stress_trend_pass:
            assessment["reasons"].append("SUCCESSIVE_PEAK_STRESS_CHANGE_AT_OR_ABOVE_5_PERCENT")
            assessment["feasibility_status"] = "NOT_FEASIBLE_OR_UNVERIFIED"
        final_stresses = [fine[k]["max_von_mises_mpa"] for k in ("compression", "tension")]
        final_displacements = [fine[k]["max_displacement_mm"] for k in ("compression", "tension")]
        margins = normalized_constraint_margins(
            fine["compression"]["max_von_mises_mpa"],
            fine["tension"]["max_von_mises_mpa"],
            max(final_displacements),
            (buckling or {}).get("lowest_positive_factor"),
            constraints,
        )
        rows.append({
            "candidate_id": candidate_id,
            "family": candidate["family"],
            "actual_cad_mass_g": candidate["actual_cad_mass_g"],
            "parameters": candidate["parameters"],
            "mesh_levels": mesh_levels,
            "successive_change_percent": deltas,
            "stress_trend_pass_lt_5_percent": stress_trend_pass,
            "buckling": buckling,
            "normalized_constraint_margins": margins,
            "assessment": assessment,
        })

    valid = [row for row in manifest + lhs_manifest if row.get("status") == "CAD_VALID"]
    invalid = [row for row in manifest + lhs_manifest if row.get("status") != "CAD_VALID"]
    paired = [
        row for row in coarse
        if row.get("compression", {}).get("status") == "FEA_SUCCESS"
        and row.get("tension", {}).get("status") == "FEA_SUCCESS"
    ]
    result = {
        "project": "Phase 4 connecting rod redesign",
        "source_branch_base": "0981e89f8189814041813b26d9dd4c2f1cd35ef1",
        "constraints": constraints.to_dict(),
        "baseline_phase3": {
            "mass_g": 735.326854,
            "compression": {
                "stress_mpa": phase3_comp["max_von_mises_mpa"],
                "displacement_mm": phase3_comp["max_displacement_mm"],
                "fos": phase3_comp["factor_of_safety"],
            },
            "tension": {
                "stress_mpa": phase3_tension["max_von_mises_mpa"],
                "displacement_mm": phase3_tension["max_displacement_mm"],
                "fos": phase3_tension["factor_of_safety"],
            },
            "reference_note": "Unsafe Phase 3 baseline; not used as a safe mass reference.",
        },
        "design_space": {
            "studies": [
                {
                    "sampling_method": "Seeded bounded random sampling",
                    "seed": 20261110,
                    "attempts": len(manifest),
                    "valid_cad": sum(row.get("status") == "CAD_VALID" for row in manifest),
                    "invalid_or_duplicate": sum(row.get("status") != "CAD_VALID" for row in manifest),
                    "coarse_candidates": len([r for r in coarse_random if r.get("compression", {}).get("status") == "FEA_SUCCESS" and r.get("tension", {}).get("status") == "FEA_SUCCESS"]),
                    "coarse_load_case_labels": 2 * len([r for r in coarse_random if r.get("compression", {}).get("status") == "FEA_SUCCESS" and r.get("tension", {}).get("status") == "FEA_SUCCESS"]),
                },
                {
                    "sampling_method": "SciPy family-wise Latin hypercube",
                    "seed": 20261111,
                    "attempts": len(lhs_manifest),
                    "valid_cad": sum(row.get("status") == "CAD_VALID" for row in lhs_manifest),
                    "invalid_or_duplicate": sum(row.get("status") != "CAD_VALID" for row in lhs_manifest),
                    "coarse_candidates": len([r for r in coarse_lhs if r.get("compression", {}).get("status") == "FEA_SUCCESS" and r.get("tension", {}).get("status") == "FEA_SUCCESS"]),
                    "coarse_load_case_labels": 2 * len([r for r in coarse_lhs if r.get("compression", {}).get("status") == "FEA_SUCCESS" and r.get("tension", {}).get("status") == "FEA_SUCCESS"]),
                },
            ],
            "total_attempts": len(manifest) + len(lhs_manifest),
            "total_valid_cad": len(valid),
            "total_invalid_or_duplicate": len(invalid),
            "valid_by_family": {family: sum(x["family"] == family for x in valid) for family in sorted({x["family"] for x in manifest + lhs_manifest})},
            "coarse_mass_stratified_candidates": len(paired),
            "coarse_load_case_labels": len(paired) * 2,
            "coarse_mesh_mm": 6.0,
            "coarse_results_are_feasibility_declarations": False,
        },
        "refined_candidates": rows,
        "convergence_note": (
            "Two independently generated local meshes (1.25 and 0.75 mm targets) are nonnested. "
            "The <5% successive peak-stress test is provisional and not a GCI or continuum error bound. "
            "The maximum unaveraged integration-point peak is retained without smoothing."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    coarse_frame = []
    for study_name, source in (("Seeded random", coarse_random), ("Latin hypercube", coarse_lhs)):
        for row in source:
            for kind in ("compression", "tension"):
                case = row.get(kind, {})
                coarse_frame.append({
                    "candidate_id": f"{study_name.split()[0][0]}-{row['candidate_id']}",
                    "study": study_name,
                    "family": row.get("family"),
                    "mass_g": row.get("actual_cad_mass_g"),
                    "load": kind,
                    "mesh_mm": row.get("mesh_mm"),
                    "status": case.get("status"),
                    "max_stress_mpa": case.get("max_von_mises_mpa"),
                    "factor_of_safety": case.get("factor_of_safety"),
                    "max_displacement_mm": case.get("max_displacement_mm"),
                    "allowable_mpa": constraints.allowable_stress_mpa,
                })
    (OUT.parent / "family-screen.json").write_text(json.dumps(coarse_frame, indent=2), encoding="utf-8")
    (OUT.parent / "design-space-summary.json").write_text(json.dumps({
        "total_attempts": result["design_space"]["total_attempts"],
        "valid_cad_candidates": result["design_space"]["total_valid_cad"],
        "invalid_or_duplicate_candidates": result["design_space"]["total_invalid_or_duplicate"],
        "valid_by_family": result["design_space"]["valid_by_family"],
        "coarse_fea_candidate_ids": [r["candidate_id"] for r in coarse_frame if r["load"] == "compression"],
        "sampling_studies": result["design_space"]["studies"],
        "coarse_fea_load_case_labels": result["design_space"]["coarse_load_case_labels"],
    }, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "designs": result["design_space"],
        "candidates": [
            {"id": r["candidate_id"], "mass_g": r["actual_cad_mass_g"],
             "assessment": r["assessment"]["feasibility_status"],
             "stress_delta_percent": r["assessment"]["mesh_stress_trend_max_percent"]}
            for r in rows
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
