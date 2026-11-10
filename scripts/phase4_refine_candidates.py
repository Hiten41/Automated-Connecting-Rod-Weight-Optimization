"""Run paired local mesh-level studies and linear buckling for selected designs."""

import argparse
import json
from pathlib import Path

from conrod.buckling import run_linear_buckling
from conrod.design_families import FamilyDesign
from conrod.fea import ROOT, solve
from conrod.materials import MATERIALS
from conrod.phase4 import (
    assess_candidate,
    finest_successful_mesh_level,
    mesh_refinement_summary,
    ordered_mesh_levels,
    static_pair_passes,
)
from conrod.schemas import LoadCase, MeshSettings, Mode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="+", required=True)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/phase4-design-space")
    parser.add_argument("--levels", nargs="+", type=float, default=[1.25, 0.75])
    parser.add_argument("--bulk-mm", type=float, default=4.0)
    args = parser.parse_args()

    manifest = json.loads((args.root / "manifest.json").read_text())
    by_id = {
        row["candidate_id"]: row for row in manifest if row.get("status") == "CAD_VALID"
    }
    material = MATERIALS["Forged Steel (AISI 4340)"]
    root = ROOT / "runs/phase4-refined"
    root.mkdir(parents=True, exist_ok=True)
    summary_path = root / "summary.json"
    all_summaries = (
        json.loads(summary_path.read_text()) if summary_path.exists() else []
    )

    for candidate_id in args.candidates:
        if candidate_id not in by_id:
            raise ValueError(f"Unknown CAD_VALID candidate: {candidate_id}")
        candidate = by_id[candidate_id]
        design = FamilyDesign(**candidate["parameters"])
        level_results = {}
        levels = tuple(float(value) for value in ordered_mesh_levels(args.levels))
        for level in levels:
            level_dir = root / candidate_id / f"local-{level:g}mm"
            settings = MeshSettings(
                size_mm=args.bulk_mm,
                hotspot_size_mm=level,
                local_refinement=True,
                refinement_region="big_end_transition",
            )
            case_results = {}
            for kind, force in (("compression", 28000), ("tension", 18000)):
                out = level_dir / kind
                existing = out / "result.json"
                if existing.exists():
                    result = json.loads(existing.read_text())
                else:
                    mesh_source = (
                        level_dir / "compression" if kind == "tension" else None
                    )
                    result = solve(
                        design,
                        material,
                        LoadCase(kind, force),
                        settings,
                        out,
                        Mode.FEA,
                        mesh_source=mesh_source,
                    )
                case_results[kind] = result
                print(
                    json.dumps(
                        {
                            "candidate_id": candidate_id,
                            "level_mm": level,
                            "case": kind,
                            "status": result.get("status"),
                            "stress_mpa": result.get("max_von_mises_mpa"),
                            "displacement_mm": result.get("max_displacement_mm"),
                            "nodes": result.get("node_count"),
                            "elements": result.get("element_count"),
                        }
                    ),
                    flush=True,
                )
                if result.get("status") != "FEA_SUCCESS":
                    break
            level_results[str(level)] = case_results

        selected_level = finest_successful_mesh_level(level_results)
        fine = level_results.get(selected_level, {}) if selected_level else {}
        refinement = mesh_refinement_summary(level_results)
        buckling = None
        compression = fine.get("compression", {})
        stress_allowable = 710.0 / 1.8
        both_static_cases_pass = static_pair_passes(
            fine, stress_allowable, maximum_displacement_mm=0.35
        )
        if both_static_cases_pass:
            buckling = run_linear_buckling(
                compression["output_dir"]
                and Path(compression["output_dir"]) / "job.inp",
                root / candidate_id / f"local-{float(selected_level):g}mm" / "buckling",
            )
        else:
            buckling = {
                "status": "NOT_RUN_STATIC_CONSTRAINT_FAILED",
                "note": "Linear buckling is only run after both fine static load cases pass stress and displacement limits.",
            }
        fine_cases = {k: v for k, v in fine.items() if k in ("compression", "tension")}
        input_deck = (
            str((buckling or {}).get("input_deck", "")).replace("\\", "/").lower()
        )
        expected_mesh_fragment = (
            f"local-{float(selected_level):g}mm/buckling/".lower()
            if selected_level
            else ""
        )
        buckling_mesh_matches = bool(
            selected_level
            and (buckling or {}).get("status") == "BUCKLING_SUCCESS"
            and expected_mesh_fragment in input_deck
        )
        if buckling:
            buckling["mesh_level_mm"] = (
                float(selected_level) if selected_level else None
            )
            buckling["mesh_association_status"] = (
                "PASS" if buckling_mesh_matches else "UNVERIFIED"
            )
        assessment = assess_candidate(
            fine_cases,
            buckling_factor=(buckling or {}).get("lowest_positive_factor")
            if buckling_mesh_matches
            else None,
            cad_validity_status=candidate.get("status"),
            mesh_refinement_status=refinement["status"],
            buckling_mesh_matches=buckling_mesh_matches,
            finest_mesh_level_mm=float(selected_level) if selected_level else None,
        )
        summary = {
            "candidate_id": candidate_id,
            "family": candidate["family"],
            "mass_g": candidate["actual_cad_mass_g"],
            "parameters": candidate["parameters"],
            "mesh_levels_mm": levels,
            "assessment_mesh_level_mm": float(selected_level)
            if selected_level
            else None,
            "bulk_mesh_mm": args.bulk_mm,
            "mesh_region": "big_end_transition",
            "mesh_refinement": refinement,
            "level_results": {
                level: {
                    kind: {
                        "status": result.get("status"),
                        "stress_mpa": result.get("max_von_mises_mpa"),
                        "displacement_mm": result.get("max_displacement_mm"),
                        "nodes": result.get("node_count"),
                        "elements": result.get("element_count"),
                        "runtime_s": result.get("runtime_s"),
                        "output_dir": result.get("output_dir"),
                    }
                    for kind, result in cases.items()
                }
                for level, cases in level_results.items()
            },
            "buckling": buckling,
            "assessment": assessment,
        }
        all_summaries = [
            r for r in all_summaries if r.get("candidate_id") != candidate_id
        ]
        all_summaries.append(summary)
        summary_path.write_text(json.dumps(all_summaries, indent=2))

    print(json.dumps(all_summaries, indent=2))


if __name__ == "__main__":
    main()
