"""Build the Phase 4 provenance-rich dataset from solver result files."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = ROOT / "data/phase4/fea-dataset.jsonl"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def design_hash(parameters):
    canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def append_result(rows, row, result, fidelity, study, buckling=None):
    geometry = row["parameters"]
    rows.append({
        "study": study,
        "candidate_id": row["candidate_id"],
        "geometry_family": row["family"],
        "geometry_parameters": geometry,
        "geometry_hash": design_hash(geometry),
        "cad_mass_g": row["actual_cad_mass_g"],
        "load_case": result.get("load", {}).get("kind"),
        "load_force_n": result.get("load", {}).get("force_n"),
        "boundary_condition_version": result.get("mesh", {}).get("boundary_mode"),
        "mesh_fidelity": fidelity,
        "mesh_settings": result.get("mesh"),
        "solver_status": result.get("status"),
        "peak_unaveraged_ip_von_mises_mpa": result.get("max_von_mises_mpa"),
        "max_displacement_mm": result.get("max_displacement_mm"),
        "factor_of_safety_on_710_mpa": result.get("factor_of_safety"),
        "buckling_factor": buckling,
        "solver_version": result.get("solver_version"),
        "gmsh_version": result.get("gmsh_version"),
        "sample_id": result.get("sample_id"),
        "raw_result_path": result.get("output_dir"),
        "fields_path": result.get("fields_path"),
    })


def main():
    rows = []
    studies = (
        ("seeded_random", RUNS / "phase4-design-space", "6mm_coarse"),
        ("latin_hypercube", RUNS / "phase4-design-space-lhs", "6mm_coarse"),
    )
    for study, root, fidelity in studies:
        manifest = read(root / "manifest.json")
        screen = read(root / "fea/screen.json")
        design_by_id = {x["candidate_id"]: x for x in manifest if x.get("status") == "CAD_VALID"}
        for candidate in screen:
            source = design_by_id[candidate["candidate_id"]]
            row = {
                "candidate_id": candidate["candidate_id"],
                "family": candidate["family"],
                "parameters": source["parameters"],
                "actual_cad_mass_g": candidate["actual_cad_mass_g"],
            }
            for kind in ("compression", "tension"):
                result = candidate[kind]
                append_result(rows, row, result, fidelity, study)

    evidence = read(ROOT / "data/phase4/phase4-evidence.json")
    final_ids = {x["candidate_id"] for x in evidence["refined_candidates"]}
    for final in evidence["refined_candidates"]:
        study = "latin_hypercube" if final["candidate_id"] == "P4-0065" else "seeded_random"
        for level, cases in final["mesh_levels"].items():
            buckling = (
                (final.get("buckling") or {}).get("lowest_positive_factor")
                if level == min(final["mesh_levels"], key=float)
                else None
            )
            for kind in ("compression", "tension"):
                path = RUNS / "phase4-refined" / final["candidate_id"] / f"local-{level}mm" / kind / "result.json"
                result = read(path)
                row = {
                    "candidate_id": final["candidate_id"],
                    "family": final["family"],
                    "parameters": final["parameters"],
                    "actual_cad_mass_g": final["actual_cad_mass_g"],
                }
                append_result(rows, row, result, f"local_{level}mm", study, buckling if kind == "compression" else None)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
    summary = {
        "records": len(rows),
        "coarse_load_case_records": sum("coarse" in row["mesh_fidelity"] for row in rows),
        "refined_load_case_records": sum("local_" in row["mesh_fidelity"] for row in rows),
        "distinct_geometry_hashes": len({row["geometry_hash"] for row in rows}),
        "fine_geometry_groups": len(final_ids),
        "output": str(OUT),
        "note": "The file preserves geometry grouping and solver provenance; mesh fidelities and load cases are not statistically independent rows.",
    }
    (OUT.parent / "dataset-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
