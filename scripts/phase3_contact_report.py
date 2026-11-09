"""Assemble contact evidence from actual CalculiX patch and pin/ring runs."""

import hashlib
import json

from conrod.fea import ROOT


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    out = ROOT / "evidence/phase3/contact-validation.json"
    prior = json.loads(out.read_text(encoding="utf-8"))
    root = ROOT / "runs/phase3-pin-benchmark"
    pin_rows = json.loads((root / "results.json").read_text(encoding="utf-8"))
    for row in pin_rows:
        case = root / f"n{row['angular_elements']}-k{row['penalty']:g}"
        row["raw_files"] = {
            name: {
                "path": str((case / name).relative_to(ROOT)),
                "sha256": sha256(case / name),
            }
            for name in ["job.inp", "job.dat", "solver.log"]
        }

    base, fine, stiff = pin_rows[0], pin_rows[2], pin_rows[3]
    mesh_pressure_change = (
        abs(base["peak_contact_pressure_mpa"] - fine["peak_contact_pressure_mpa"])
        / base["peak_contact_pressure_mpa"]
    )
    penalty_pressure_change = (
        abs(stiff["peak_contact_pressure_mpa"] - fine["peak_contact_pressure_mpa"])
        / fine["peak_contact_pressure_mpa"]
    )
    penalty_force_change = abs(stiff["pin_force_n"][0] - fine["pin_force_n"][0]) / abs(
        fine["pin_force_n"][0]
    )
    max_balance = max(row["equilibrium_fraction"] for row in pin_rows)

    evidence = {
        "patch_tests": prior["patch_tests"],
        "pin_tests": pin_rows,
        "pin_status": "NOT VALIDATED FOR ROD INTEGRATION",
        "primary_model": "COSINE_BEARING equivalent-pressure approximation",
        "benchmark_definition": {
            "solver": "CalculiX 2.22",
            "elements": "C3D8 full-integration bricks",
            "angular_sectors": [32, 64, 96],
            "radial_elements_per_body": 3,
            "axial_layers": 1,
            "pin_outer_radius_mm": 9.99,
            "ring_bore_radius_mm": 10.0,
            "radial_clearance_mm": 0.01,
            "ring_outer_radius_mm": 14.0,
            "thickness_mm": 1.0,
            "imposed_pin_translation_mm": 0.02,
            "normal_penalties_mpa_per_mm": [1000000.0, 10000000.0],
            "friction": "frictionless; no tangential law",
            "pin_motion": "all pin nodes are prescribed to the same rigid translation; no reference-node coupling",
            "contact_faces": "pin outer C3D8 S4 slave; ring bore C3D8 S6 master",
        },
        "checks": {
            "max_relative_reaction_imbalance": max_balance,
            "reaction_equilibrium_passed": max_balance < 1e-6,
            "peak_pressure_relative_change_32_to_96": mesh_pressure_change,
            "peak_pressure_relative_change_penalty_1e6_to_1e7_at_96": penalty_pressure_change,
            "resultant_force_relative_change_penalty_1e6_to_1e7_at_96": penalty_force_change,
            "provisional_change_target": 0.05,
            "pressure_sensitivity_passed": max(
                mesh_pressure_change, penalty_pressure_change
            )
            < 0.05,
        },
        "conclusion": (
            "Reaction equilibrium is excellent, and the measured face-level pressure "
            "is consistent with the specified linear penalty and signed penetration. "
            "Peak pressure remains sensitive to angular mesh and penalty stiffness; "
            "this benchmark is not qualified for integration into the connecting-rod model."
        ),
        "limitations": [
            "This is an idealized rigid-translation pin and ring benchmark, not a connecting rod.",
            "The ring outer boundary is fixed and the thickness direction is constrained.",
            "The pin is kinematically prescribed at all nodes rather than attached to a reference node.",
            "The study does not establish a converged contact-pressure field or validate bore stress in a rod.",
            "Failed surface-selection and input-format attempts are retained under runs/phase3-failed-attempts and excluded from the measurements above.",
        ],
        "source": "CalculiX 2.22 User's Manual, *SURFACE C3D8 face numbering and contact sections 6.7, 7.22–7.23: https://www.dhondt.de/ccx_2.22.pdf",
    }
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence["checks"], indent=2))


if __name__ == "__main__":
    run()
