"""Refine the closest coarse-FEA geometries without accepting ML predictions."""

import json
import argparse
from conrod.fea import ROOT, solve
from conrod.materials import MATERIALS
from conrod.schemas import Geometry, LoadCase, MeshSettings


def run(count=4):
    study = ROOT / "data/phase3/feasibility/candidates.json"
    rows = json.loads(study.read_text(encoding="utf-8"))
    ranked = []
    for row in rows:
        ok = [x for x in row.get("results", []) if x.get("status") == "FEA_SUCCESS"]
        if len(ok) != 2:
            continue
        worst = max(x["max_von_mises_mpa"] / (710 / 1.8) for x in ok)
        ranked.append((worst, row))
    ranked.sort(key=lambda x: x[0])
    root = ROOT / "data/phase3/near-boundary"
    root.mkdir(parents=True, exist_ok=True)
    output = []
    for ratio, row in ranked[:count]:
        g = Geometry(**row["parameters"])
        case = root / str(row["index"])
        results = []
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
                    MeshSettings(
                        4, hotspot_size_mm=0.75, refinement_region="big_end_transition"
                    ),
                    out,
                    mesh_source=case / "compression"
                    if kind == "tension"
                    and (case / "compression/mesh-topology.json").exists()
                    else None,
                )
            results.append(r)
            print(
                row["index"],
                kind,
                r["status"],
                r.get("max_von_mises_mpa"),
                r.get("node_count"),
                flush=True,
            )
            if r["status"] != "FEA_SUCCESS":
                break
        output.append(
            dict(
                candidate_id=row["index"],
                coarse_worst_stress_ratio=ratio,
                results=results,
                status="REFINED_SCREEN_ONLY"
                if len(results) == 2
                and all(r["status"] == "FEA_SUCCESS" for r in results)
                else "INCOMPLETE",
            )
        )
        (root / "results.json").write_text(
            json.dumps(output, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=4)
    run(parser.parse_args().count)
