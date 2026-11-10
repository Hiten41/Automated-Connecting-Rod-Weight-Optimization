"""Deterministic Phase 4 CAD search with optional paired coarse FEA screening."""

import argparse
import json
from pathlib import Path

from conrod.design_families import FAMILIES, FamilyDesign
from conrod.design_exploration import lhs_designs, mass_stratified_candidates
from conrod.fea import cad, solve
from conrod.materials import MATERIALS, mass_from_volume
from conrod.phase4 import assess_candidate
from conrod.schemas import LoadCase, MeshSettings, Mode


def axial_area_mm2(design):
    """Gross section-area screen; ignores local bending and notch concentrations."""
    f, w, h = design.flange_thickness_mm, design.web_thickness_mm, design.beam_thickness
    family = "h_section" if design.family in ("h_section", "pocket_variant") else "i_section"

    def area(width):
        if family == "h_section":
            return 2 * f * h + w * (width - 2 * f)
        return 2 * width * f + w * (h - 2 * f)

    if design.family != "tapered":
        return area(design.section_width)
    widths = [design.taper_big_width_mm, design.taper_big_width_mm,
              design.taper_mid_width_mm, design.taper_small_width_mm,
              design.taper_small_width_mm]
    x = [0, .16, .52, .86, 1.0]
    section_areas = [area(w) for w in widths]
    return float(sum((x[i + 1] - x[i]) * (section_areas[i + 1] + section_areas[i]) / 2
                     for i in range(len(x) - 1)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/phase4-design-space"))
    parser.add_argument("--target-per-family", type=int, default=12)
    parser.add_argument("--max-attempts-per-family", type=int, default=24)
    parser.add_argument("--run-screen", action="store_true")
    parser.add_argument("--fea-per-family", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--mesh-mm", type=float, default=6.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    attempts_by_family = {name: 0 for name in FAMILIES}
    target_count = {name: 0 for name in FAMILIES}
    seen = set()
    lhs_samples = {
        name: lhs_designs(name, args.max_attempts_per_family, args.seed + index)
        for index, name in enumerate(FAMILIES)
    }
    for family in FAMILIES:
        while target_count[family] < args.target_per_family and attempts_by_family[family] < args.max_attempts_per_family:
            attempts_by_family[family] += 1
            candidate_id = f"P4-{len(manifest) + 1:04d}"
            record = {"candidate_id": candidate_id, "family": family, "seed": args.seed}
            try:
                design = lhs_samples[family][attempts_by_family[family] - 1]
                design.validate()
                key = tuple(sorted(design.to_dict().items()))
                if key in seen:
                    record.update(status="INVALID_DUPLICATE", parameters=design.to_dict())
                    manifest.append(record)
                    continue
                seen.add(key)
                record["parameters"] = design.to_dict()
                (args.output / "designs").mkdir(exist_ok=True)
                cad_dir = args.output / "designs" / candidate_id
                meta = cad(design, cad_dir)
                material = MATERIALS["Forged Steel (AISI 4340)"]
                mass_kg = mass_from_volume(meta["volume_mm3"], material)
                area = axial_area_mm2(design)
                record.update(
                    status="CAD_VALID",
                    geometry_version=design.geometry_version,
                    volume_mm3=meta["volume_mm3"],
                    actual_cad_mass_g=mass_kg * 1000,
                    solid_count=meta["solid_count"],
                    bore_count=len(meta["bores"]),
                    bore_center_distance_mm=meta["bore_center_distance_mm"],
                    bores=meta["bores"],
                    transition_edges_filleted=meta["transition_edges_filleted"],
                    gross_section_area_mm2=area,
                    nominal_axial_stress_28kN_mpa=28000 / area,
                    nominal_axial_stress_18kN_mpa=18000 / area,
                    cad_output=str(cad_dir),
                )
                target_count[family] += 1
            except Exception as exc:
                record.update(status="CAD_INVALID", error=str(exc))
                try:
                    record["cad_error"] = json.loads((args.output / "designs" / candidate_id / "cad.json").read_text())
                except Exception:
                    pass
            manifest.append(record)
            (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
            print(json.dumps(record), flush=True)

    valid = [r for r in manifest if r["status"] == "CAD_VALID"]
    selected_ids = []
    if args.run_screen:
        material = MATERIALS["Forged Steel (AISI 4340)"]
        mesh = MeshSettings(size_mm=args.mesh_mm, local_refinement=False)
        screened = []
        for candidate in mass_stratified_candidates(valid, args.fea_per_family):
            family = candidate["family"]
            selected_ids.append(candidate["candidate_id"])
            design = FamilyDesign(**candidate["parameters"])
            case_results = {}
            comp_dir = args.output / "fea" / candidate["candidate_id"] / "compression"
            comp = solve(design, material, LoadCase("compression", 28000), mesh, comp_dir, Mode.FEA)
            case_results["compression"] = comp
            tens_dir = args.output / "fea" / candidate["candidate_id"] / "tension"
            tens = solve(design, material, LoadCase("tension", 18000), mesh, tens_dir, Mode.FEA,
                         mesh_source=comp_dir if comp.get("status") == "FEA_SUCCESS" else None)
            case_results["tension"] = tens
            screen = assess_candidate(case_results)
            record = {
                "candidate_id": candidate["candidate_id"], "family": family,
                "actual_cad_mass_g": candidate["actual_cad_mass_g"],
                "mesh_settings": mesh.to_dict(),
                "compression": {k: comp.get(k) for k in ("status", "max_von_mises_mpa", "max_displacement_mm", "factor_of_safety", "node_count", "element_count", "runtime_s", "hotspot", "mesh_quality")},
                "tension": {k: tens.get(k) for k in ("status", "max_von_mises_mpa", "max_displacement_mm", "factor_of_safety", "node_count", "element_count", "runtime_s", "hotspot", "mesh_quality")},
                "assessment": screen,
                "compression_output": str(comp_dir), "tension_output": str(tens_dir),
            }
            screened.append(record)
            (args.output / "fea-screen.json").write_text(json.dumps(screened, indent=2))
            print(json.dumps(record), flush=True)

    summary = {
        "seed": args.seed,
        "sampling_method": "SciPy LatinHypercube (family-wise, reproducible seed)",
        "families": list(FAMILIES),
        "target_per_family": args.target_per_family,
        "attempts_by_family": attempts_by_family,
        "valid_by_family": {f: sum(r["family"] == f and r["status"] == "CAD_VALID" for r in manifest) for f in FAMILIES},
        "invalid_by_family": {f: sum(r["family"] == f and r["status"] != "CAD_VALID" for r in manifest) for f in FAMILIES},
        "total_attempts": len(manifest),
        "valid_cad_candidates": len(valid),
        "invalid_or_duplicate_candidates": len(manifest) - len(valid),
        "coarse_fea_candidate_ids": selected_ids,
        "classification": "CAD/actual-mass and optional coarse-FEA design exploration; not a proof of global infeasibility or structural qualification",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
