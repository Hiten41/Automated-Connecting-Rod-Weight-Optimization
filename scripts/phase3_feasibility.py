"""Space-filling, checkpointed feasibility study; no surrogate acceptance."""

import argparse
import json
from scipy.stats import qmc
from conrod.fea import ROOT, solve, cad
from conrod.schemas import Geometry, LoadCase, MeshSettings, BOUNDS
from conrod.materials import MATERIALS, mass_from_volume
from conrod.analytical import evaluate

KEYS = [
    "ring_thickness",
    "shank_width",
    "beam_thickness",
    "pocket_depth",
    "flange_thickness",
    "transition_radius_mm",
]


def designs(count=40):
    # Fixed bore sizes and center distance define the installation envelope.
    samples = qmc.LatinHypercube(d=len(KEYS), seed=7301).random(count)
    return [
        dict(zip(KEYS, qmc.scale(samples, *zip(*(BOUNDS[k] for k in KEYS)))[i]))
        for i in range(count)
    ]


def assess(results):
    if len(results) != 2 or any(r.get("status") != "FEA_SUCCESS" for r in results):
        return dict(status="SOLVER_FAILURE_OR_UNCERTAIN")
    margins = []
    for r in results:
        a = evaluate(
            Geometry(**r["geometry"]),
            MATERIALS["Forged Steel (AISI 4340)"],
            LoadCase(**r["load"]),
        )
        margins.append(
            dict(
                kind=r["load"]["kind"],
                stress_mpa=710 / 1.8 - r["max_von_mises_mpa"],
                displacement_mm=0.35 - r["max_displacement_mm"],
                buckling_margin=None
                if a["buckling_margin"] is None
                else a["buckling_margin"] - 1.8,
            )
        )
    passed = all(
        m["stress_mpa"] >= 0
        and m["displacement_mm"] >= 0
        and (m["buckling_margin"] is None or m["buckling_margin"] >= 0)
        for m in margins
    )
    return dict(
        status="PROVISIONAL_SINGLE_MESH_PASS"
        if passed
        else "INFEASIBLE_ON_TESTED_MESH",
        margins=margins,
        qualification="No convergence-qualified acceptance from coarse screening",
    )


def run(limit=6, count=40):
    root = ROOT / "data/phase3/feasibility"
    root.mkdir(parents=True, exist_ok=True)
    plan = designs(count)
    (root / "sampling-plan.json").write_text(
        json.dumps(
            dict(
                seed=7301,
                keys=KEYS,
                bounds={k: BOUNDS[k] for k in KEYS},
                fixed_packaging=dict(length_cc=145, big_end_id=50, small_end_id=24),
                designs=plan,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    records = []
    material = MATERIALS["Forged Steel (AISI 4340)"]
    for i, values in enumerate(plan[:limit]):
        folder = root / "cases" / f"{i:03d}"
        folder.mkdir(parents=True, exist_ok=True)
        checkpoint = folder / "candidate.json"
        if checkpoint.exists():
            previous = json.loads(checkpoint.read_text(encoding="utf-8"))
            if previous["parameters"] != values:
                raise ValueError(
                    "Resume sampling plan differs; use a new versioned dataset directory"
                )
            records.append(previous)
            continue
        row = dict(index=i, parameters=values)
        try:
            g = Geometry(**values).validate()
            meta = cad(g, folder / "cad")
            row.update(cad=meta, mass_kg=mass_from_volume(meta["volume_mm3"], material))
            row["analytical"] = [
                evaluate(g, material, LoadCase(k, f), meta["volume_mm3"])
                for k, f in [("compression", 28000), ("tension", 18000)]
            ]
            results = []
            for kind, force in [("compression", 28000), ("tension", 18000)]:
                out = folder / kind
                if (out / "result.json").exists():
                    r = json.loads((out / "result.json").read_text(encoding="utf-8"))
                else:
                    r = solve(
                        g,
                        material,
                        LoadCase(kind, force),
                        MeshSettings(6),
                        out,
                        mesh_source=folder / "compression"
                        if kind == "tension"
                        and (folder / "compression/mesh-topology.json").exists()
                        else None,
                    )
                results.append(r)
            row.update(results=results, assessment=assess(results))
        except Exception as exc:
            row.update(
                assessment=dict(status="INVALID_GEOMETRY_OR_CAD_FAILURE"),
                error=str(exc),
            )
        checkpoint.write_text(json.dumps(row, indent=2), encoding="utf-8")
        records.append(row)
        (root / "candidates.json").write_text(
            json.dumps(records, indent=2), encoding="utf-8"
        )
        print(i, row["assessment"]["status"], flush=True)
    (root / "candidates.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    return records


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=6)
    p.add_argument("--count", type=int, default=40)
    a = p.parse_args()
    run(a.limit, a.count)
