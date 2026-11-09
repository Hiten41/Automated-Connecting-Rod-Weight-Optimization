"""Generate paired, distinct-geometry fidelity data from the feasibility study.

The fine label describes mesh configuration, never an automatic convergence claim.
"""

import argparse
import hashlib
import json
import numpy as np
from conrod.fea import ROOT, solve
from conrod.schemas import Geometry, LoadCase, MeshSettings, BOUNDS
from conrod.materials import MATERIALS
from conrod.dataset import validate_record


def select(rows, count):
    usable = [
        r
        for r in rows
        if len(r.get("results", [])) == 2
        and all(x["status"] == "FEA_SUCCESS" for x in r["results"])
    ]
    if not usable:
        return []
    keys = list(usable[0]["parameters"])
    x = np.asarray(
        [
            [
                (r["parameters"][k] - BOUNDS[k][0]) / (BOUNDS[k][1] - BOUNDS[k][0])
                for k in keys
            ]
            for r in usable
        ]
    )
    # Start nearest the stress constraint, then maximize geometric coverage.
    distances = [
        abs(max(z["max_von_mises_mpa"] for z in r["results"]) - 710 / 1.8)
        for r in usable
    ]
    chosen = [int(np.argmin(distances))]
    while len(chosen) < min(count, len(usable)):
        d = np.min(
            np.linalg.norm(x[:, None, :] - x[chosen][None, :, :], axis=2), axis=1
        )
        d[chosen] = -1
        chosen.append(int(np.argmax(d)))
    return [usable[i] for i in chosen]


def run(groups=12, limit=12):
    source = ROOT / "data/phase3/feasibility/candidates.json"
    selected = select(json.loads(source.read_text(encoding="utf-8")), groups)
    root = ROOT / "data/phase3/paired"
    root.mkdir(parents=True, exist_ok=True)
    selection = root / "selection.json"
    ids = [r["index"] for r in selected]
    if selection.exists() and json.loads(selection.read_text(encoding="utf-8")) != ids:
        raise ValueError(
            "Selection changed: freeze the completed feasibility study before paired generation"
        )
    selection.write_text(json.dumps(ids), encoding="utf-8")
    # The selected geometries already have successful 6 mm compression/tension
    # results in the frozen feasibility study. Carry those records forward so
    # each geometry has three paired fidelity levels without rerunning coarse FEA.
    allrows = [
        dict(geometry_group=candidate["index"], fidelity="coarse", result=result)
        for candidate in selected[:limit]
        for result in candidate["results"]
    ]
    for candidate in selected[:limit]:
        g = Geometry(**candidate["parameters"])
        for fidelity, h in [("intermediate", 1.25), ("fine", 0.75)]:
            mesh = MeshSettings(
                4, hotspot_size_mm=h, refinement_region="big_end_transition"
            )
            case = root / "cases" / str(candidate["index"]) / fidelity
            for kind, force in [("compression", 28000), ("tension", 18000)]:
                out = case / kind
                p = out / "result.json"
                if p.exists():
                    r = json.loads(p.read_text(encoding="utf-8"))
                else:
                    r = solve(
                        g,
                        MATERIALS["Forged Steel (AISI 4340)"],
                        LoadCase(kind, force),
                        mesh,
                        out,
                        mesh_source=case / "compression"
                        if kind == "tension"
                        and (case / "compression/mesh-topology.json").exists()
                        else None,
                    )
                allrows.append(
                    dict(geometry_group=candidate["index"], fidelity=fidelity, result=r)
                )
                (root / "results.json").write_text(
                    json.dumps(allrows, indent=2), encoding="utf-8"
                )
                print(
                    candidate["index"],
                    fidelity,
                    kind,
                    r["status"],
                    r.get("max_von_mises_mpa"),
                    flush=True,
                )
                if r["status"] != "FEA_SUCCESS":
                    return
    datasets = {}
    for fidelity in ["coarse", "intermediate", "fine"]:
        valid = [
            validate_record(r["result"], "phase3-deterministic-bearing-v1")
            for r in allrows
            if r["fidelity"] == fidelity
        ]
        path = root / (fidelity + ".jsonl")
        path.write_text("".join(json.dumps(r) + "\n" for r in valid), encoding="utf-8")
        datasets[fidelity] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "analysis_count": len(valid),
            "geometry_group_count": len({r["geometry_group"] for r in allrows if r["fidelity"] == fidelity}),
            "loads": sorted({r["load"]["kind"] for r in valid}),
            "mesh": valid[0]["mesh"] if valid else None,
        }
    manifest = {
        "simulation_version": "phase3-deterministic-bearing-v1",
        "sampling_seed": 7301,
        "selection_method": "nearest coarse stress boundary followed by maximin in normalized geometry space",
        "selected_geometry_ids": ids,
        "fidelity_order": ["coarse", "intermediate", "fine"],
        "records_per_geometry_per_fidelity": 2,
        "coarse_source": "data/phase3/feasibility/candidates.json successful 6 mm compression/tension results; no duplicate solver runs",
        "coarse_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "fidelity_datasets": datasets,
        "interpretation": "mesh-level response dataset; the 0.75 mm fine label is not a universal convergence-qualified truth",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--groups", type=int, default=12)
    p.add_argument("--limit", type=int, default=12)
    a = p.parse_args()
    run(a.groups, a.limit)
