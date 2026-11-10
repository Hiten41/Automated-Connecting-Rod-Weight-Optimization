"""Consolidate compact, reproducible Phase 4 solver and design evidence."""

import json
from pathlib import Path

from conrod.design_exploration import normalized_constraint_margins
from conrod.phase4 import (
    Phase4Constraints,
    assess_candidate,
    finest_successful_mesh_level,
    mesh_refinement_summary,
    ordered_mesh_levels,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = ROOT / "data/phase4/phase4-evidence.json"
REFINED_IDS = ("P4-0055", "P4-0026", "P4-0059", "P4-0016", "P4-0060", "P4-0065")
LEVELS_BY_ID = {
    candidate_id: ("1.25", "0.75")
    for candidate_id in REFINED_IDS
    if candidate_id != "P4-0065"
}
LEVELS_BY_ID["P4-0055"] = ("1.25", "0.75", "0.5")
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
    phase3_comp = load_json(
        phase3_root / "runs/phase3-refinement/0.35-compression/result.json"
    )
    phase3_tension = load_json(
        phase3_root / "runs/phase3-refinement/0.35-tension/result.json"
    )

    rows = []
    constraints = Phase4Constraints()
    for candidate_id in REFINED_IDS:
        candidate = (
            lhs_designs[candidate_id]
            if candidate_id == "P4-0065"
            else random_designs[candidate_id]
        )
        # All reported mesh levels are ordered by their numeric target from
        # coarsest to finest (the smaller target is finer).
        levels = ordered_mesh_levels(LEVELS_BY_ID[candidate_id])
        mesh_levels = {}
        results_by_level = {}
        for level in levels:
            case_results = {}
            for kind in ("compression", "tension"):
                path = (
                    RUNS
                    / "phase4-refined"
                    / candidate_id
                    / f"local-{level}mm"
                    / kind
                    / "result.json"
                )
                if not path.is_file():
                    raise FileNotFoundError(
                        f"Missing required {kind} result for {candidate_id} at {level} mm: {path}"
                    )
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
                    "mesh_settings": result.get("mesh"),
                    "gmsh_version": result.get("gmsh_version"),
                    "solver_version": result.get("solver_version"),
                    "fields_path": result.get("fields_path"),
                    "output_dir": result.get("output_dir"),
                }
                for kind, result in case_results.items()
            }
        refinement = mesh_refinement_summary(results_by_level)
        selected_level = finest_successful_mesh_level(results_by_level)
        fine = results_by_level.get(selected_level, {}) if selected_level else {}
        buckling_path = (
            RUNS
            / "phase4-refined"
            / candidate_id
            / f"local-{selected_level}mm"
            / "buckling/buckling.json"
            if selected_level
            else None
        )
        buckling = (
            load_json(buckling_path)
            if buckling_path and buckling_path.is_file()
            else None
        )
        input_deck = (
            str((buckling or {}).get("input_deck", "")).replace("\\", "/").lower()
        )
        expected_mesh_fragment = (
            f"local-{selected_level}mm/buckling/".lower() if selected_level else ""
        )
        buckling_mesh_matches = bool(
            selected_level
            and buckling
            and (buckling or {}).get("status") == "BUCKLING_SUCCESS"
            and expected_mesh_fragment in input_deck
        )
        if buckling:
            buckling = dict(buckling)
            buckling["mesh_level_mm"] = (
                float(selected_level) if selected_level else None
            )
            buckling["mesh_association_status"] = (
                "PASS" if buckling_mesh_matches else "UNVERIFIED"
            )
        assessment = assess_candidate(
            fine,
            buckling_factor=(buckling or {}).get("lowest_positive_factor")
            if buckling_mesh_matches
            else None,
            constraints=constraints,
            cad_validity_status=candidate.get("status"),
            mesh_refinement_status=refinement["status"],
            buckling_mesh_matches=buckling_mesh_matches,
            finest_mesh_level_mm=float(selected_level) if selected_level else None,
        )
        assessment["mesh_refinement"] = refinement
        margins = None
        if (
            selected_level
            and all(
                fine.get(kind, {}).get("status") == "FEA_SUCCESS"
                for kind in ("compression", "tension")
            )
            and buckling_mesh_matches
        ):
            margins = normalized_constraint_margins(
                fine["compression"]["max_von_mises_mpa"],
                fine["tension"]["max_von_mises_mpa"],
                max(
                    fine[kind]["max_displacement_mm"]
                    for kind in ("compression", "tension")
                ),
                buckling["lowest_positive_factor"],
                constraints,
            )
        rows.append(
            {
                "candidate_id": candidate_id,
                "family": candidate["family"],
                "actual_cad_mass_g": candidate["actual_cad_mass_g"],
                "parameters": candidate["parameters"],
                "mesh_levels_coarse_to_fine_mm": [float(level) for level in levels],
                "assessment_mesh_level_mm": float(selected_level)
                if selected_level
                else None,
                "mesh_levels": mesh_levels,
                "mesh_refinement": refinement,
                # Retained for old readers; this reports only the adjacent mesh trend.
                "stress_trend_pass_lt_5_percent": refinement["status"] == "PASS",
                "buckling": buckling,
                "normalized_constraint_margins": margins,
                "assessment": assessment,
            }
        )

    valid = [row for row in manifest + lhs_manifest if row.get("status") == "CAD_VALID"]
    invalid = [
        row for row in manifest + lhs_manifest if row.get("status") != "CAD_VALID"
    ]
    paired = [
        row
        for row in coarse
        if row.get("compression", {}).get("status") == "FEA_SUCCESS"
        and row.get("tension", {}).get("status") == "FEA_SUCCESS"
    ]
    candidates_by_id = {row["candidate_id"]: row for row in rows}
    reference = candidates_by_id["P4-0055"]
    selected = candidates_by_id["P4-0065"]
    comparison_level = "0.5"
    reference_settings = reference["mesh_levels"][comparison_level]["compression"].get(
        "mesh_settings"
    )
    selected_settings = selected["mesh_levels"][comparison_level]["compression"].get(
        "mesh_settings"
    )
    matched_settings = bool(
        reference_settings
        and selected_settings
        and reference_settings == selected_settings
    )
    result = {
        "project": "Phase 4 connecting rod redesign",
        "source_branch_base": "0981e89f8189814041813b26d9dd4c2f1cd35ef1",
        "constraints": constraints.to_dict(),
        "matched_fidelity_candidate_comparison": {
            "candidate_ids": ["P4-0055", "P4-0065"],
            "local_target_mm": 0.5,
            "mesh_settings_equal": matched_settings,
            "mesh_settings": reference_settings,
            "distinct_candidate_geometries_meshed_separately": True,
            "comparison_scope": "Matched target/settings/load model/solver workflow; geometries and resulting meshes are distinct, nonnested discretizations.",
            "mass_difference_percent_p4_0065_vs_p4_0055": 100.0
            * (selected["actual_cad_mass_g"] - reference["actual_cad_mass_g"])
            / reference["actual_cad_mass_g"],
            "p4_0055_max_stress_mpa": reference["assessment"]["maximum_stress_mpa"],
            "p4_0065_max_stress_mpa": selected["assessment"]["maximum_stress_mpa"],
        },
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
                    "valid_cad": sum(
                        row.get("status") == "CAD_VALID" for row in manifest
                    ),
                    "invalid_or_duplicate": sum(
                        row.get("status") != "CAD_VALID" for row in manifest
                    ),
                    "coarse_candidates": len(
                        [
                            r
                            for r in coarse_random
                            if r.get("compression", {}).get("status") == "FEA_SUCCESS"
                            and r.get("tension", {}).get("status") == "FEA_SUCCESS"
                        ]
                    ),
                    "coarse_load_case_labels": 2
                    * len(
                        [
                            r
                            for r in coarse_random
                            if r.get("compression", {}).get("status") == "FEA_SUCCESS"
                            and r.get("tension", {}).get("status") == "FEA_SUCCESS"
                        ]
                    ),
                },
                {
                    "sampling_method": "SciPy family-wise Latin hypercube",
                    "seed": 20261111,
                    "attempts": len(lhs_manifest),
                    "valid_cad": sum(
                        row.get("status") == "CAD_VALID" for row in lhs_manifest
                    ),
                    "invalid_or_duplicate": sum(
                        row.get("status") != "CAD_VALID" for row in lhs_manifest
                    ),
                    "coarse_candidates": len(
                        [
                            r
                            for r in coarse_lhs
                            if r.get("compression", {}).get("status") == "FEA_SUCCESS"
                            and r.get("tension", {}).get("status") == "FEA_SUCCESS"
                        ]
                    ),
                    "coarse_load_case_labels": 2
                    * len(
                        [
                            r
                            for r in coarse_lhs
                            if r.get("compression", {}).get("status") == "FEA_SUCCESS"
                            and r.get("tension", {}).get("status") == "FEA_SUCCESS"
                        ]
                    ),
                },
            ],
            "total_attempts": len(manifest) + len(lhs_manifest),
            "total_valid_cad": len(valid),
            "total_invalid_or_duplicate": len(invalid),
            "valid_by_family": {
                family: sum(x["family"] == family for x in valid)
                for family in sorted({x["family"] for x in manifest + lhs_manifest})
            },
            "coarse_mass_stratified_candidates": len(paired),
            "coarse_load_case_labels": len(paired) * 2,
            "coarse_mesh_mm": 6.0,
            "coarse_results_are_feasibility_declarations": False,
        },
        "refined_candidates": rows,
        "status_semantics": {
            "recorded_screen_status": "Recorded stress, displacement and associated linear buckling limits only.",
            "mesh_refinement_status": "Adjacent nonnested mesh peak-stress trend only; not continuum convergence.",
            "independent_solver_status": "NOT_PERFORMED for every candidate.",
            "mechanical_qualification_status": "NOT_QUALIFIED for every candidate.",
            "optimization_eligibility": "NOT_QUALIFIED for every candidate.",
            "feasibility_status": "Legacy field retained as non-passing; use explicit status fields.",
        },
        "convergence_note": (
            "Mesh targets are numerically ordered coarse to fine and the last adjacent pair is used for the trend. "
            "The meshes are nonnested; a <5% successive peak-stress change is not a GCI or continuum error bound. "
            "The maximum unaveraged integration-point peak is retained without smoothing."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    coarse_frame = []
    for study_name, source in (
        ("Seeded random", coarse_random),
        ("Latin hypercube", coarse_lhs),
    ):
        for row in source:
            for kind in ("compression", "tension"):
                case = row.get(kind, {})
                coarse_frame.append(
                    {
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
                    }
                )
    (OUT.parent / "family-screen.json").write_text(
        json.dumps(coarse_frame, indent=2), encoding="utf-8"
    )
    (OUT.parent / "design-space-summary.json").write_text(
        json.dumps(
            {
                "total_attempts": result["design_space"]["total_attempts"],
                "valid_cad_candidates": result["design_space"]["total_valid_cad"],
                "invalid_or_duplicate_candidates": result["design_space"][
                    "total_invalid_or_duplicate"
                ],
                "valid_by_family": result["design_space"]["valid_by_family"],
                "coarse_fea_candidate_ids": [
                    r["candidate_id"]
                    for r in coarse_frame
                    if r["load"] == "compression"
                ],
                "sampling_studies": result["design_space"]["studies"],
                "coarse_fea_load_case_labels": result["design_space"][
                    "coarse_load_case_labels"
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUT),
                "designs": result["design_space"],
                "candidates": [
                    {
                        "id": r["candidate_id"],
                        "mass_g": r["actual_cad_mass_g"],
                        "recorded_screen_status": r["assessment"][
                            "recorded_screen_status"
                        ],
                        "mesh_refinement_status": r["assessment"][
                            "mesh_refinement_status"
                        ],
                        "assessment_mesh_level_mm": r["assessment"][
                            "finest_mesh_level_mm"
                        ],
                        "maximum_stress_mpa": r["assessment"]["maximum_stress_mpa"],
                    }
                    for r in rows
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
