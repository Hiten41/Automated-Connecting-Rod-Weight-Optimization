"""Paired coarse FEA for a mass-stratified subset of Phase 4 CAD candidates."""

import argparse
import json
from pathlib import Path

from conrod.design_families import FAMILIES, FamilyDesign
from conrod.design_exploration import mass_stratified_candidates
from conrod.fea import solve
from conrod.materials import MATERIALS
from conrod.phase4 import assess_candidate
from conrod.schemas import LoadCase, MeshSettings, Mode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("runs/phase4-design-space"))
    parser.add_argument("--per-family", type=int, default=3)
    parser.add_argument("--mesh-mm", type=float, default=6.0)
    args = parser.parse_args()
    manifest = json.loads((args.root / "manifest.json").read_text())
    valid = [row for row in manifest if row.get("status") == "CAD_VALID"]
    material = MATERIALS["Forged Steel (AISI 4340)"]
    mesh = MeshSettings(size_mm=args.mesh_mm, local_refinement=False)
    out = args.root / "fea"
    out.mkdir(exist_ok=True)
    screen_path = out / "screen.json"
    records = json.loads(screen_path.read_text()) if screen_path.exists() else []
    completed = {
        row["candidate_id"]: row
        for row in records
        if row.get("compression", {}).get("status") == "FEA_SUCCESS"
        and row.get("tension", {}).get("status") == "FEA_SUCCESS"
    }
    for candidate in mass_stratified_candidates(valid, args.per_family):
        family = candidate["family"]
        if candidate["candidate_id"] in completed:
            continue
        design = FamilyDesign(**candidate["parameters"])
        case_results = {}
        cdir = out / candidate["candidate_id"] / "compression"
        comp = solve(design, material, LoadCase("compression", 28000), mesh, cdir, Mode.FEA)
        case_results["compression"] = comp
        tdir = out / candidate["candidate_id"] / "tension"
        tens = solve(
            design, material, LoadCase("tension", 18000), mesh, tdir, Mode.FEA,
            mesh_source=cdir if comp.get("status") == "FEA_SUCCESS" else None,
        )
        case_results["tension"] = tens
        record = {
            "candidate_id": candidate["candidate_id"],
            "family": family,
            "actual_cad_mass_g": candidate["actual_cad_mass_g"],
            "parameters": candidate["parameters"],
            "mesh_mm": args.mesh_mm,
            "mesh_configuration": mesh.to_dict(),
            "compression": comp,
            "tension": tens,
            "assessment": assess_candidate(case_results),
        }
        records = [r for r in records if r.get("candidate_id") != candidate["candidate_id"]]
        records.append(record)
        screen_path.write_text(json.dumps(records, indent=2))
        print(json.dumps({
            "candidate_id": candidate["candidate_id"], "family": family,
            "mass_g": candidate["actual_cad_mass_g"],
            "compression_status": comp.get("status"),
            "compression_stress_mpa": comp.get("max_von_mises_mpa"),
            "tension_status": tens.get("status"),
            "tension_stress_mpa": tens.get("max_von_mises_mpa"),
            "feasibility": record["assessment"]["feasibility_status"],
        }), flush=True)
    summary = {
        "screened_candidates": len(records),
        "completed_paired_candidates": sum(
            r.get("compression", {}).get("status") == "FEA_SUCCESS"
            and r.get("tension", {}).get("status") == "FEA_SUCCESS"
            for r in records
        ),
        "load_case_labels": sum(
            r["compression"].get("status") == "FEA_SUCCESS"
            for r in records
        ) + sum(r["tension"].get("status") == "FEA_SUCCESS" for r in records),
        "per_family": {
            f: sum(r["family"] == f for r in records) for f in FAMILIES
        },
        "mesh": mesh.to_dict(),
        "screen_only": True,
        "note": "Mass-stratified paired 6 mm FEA; coarse results are not feasible-design declarations.",
    }
    (out / "screen-summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
