"""Bounded repeatability pilot before finer structural solves."""

import json
from conrod.fea import ROOT, cad, mesh_step
from conrod.schemas import Geometry, MeshSettings


def run():
    root = ROOT / "runs/phase3-mesh-pilot"
    root.mkdir(parents=True, exist_ok=True)
    g = Geometry()
    cad(g, root)
    records = []
    for name, size in [("repeat-a", 0.75), ("repeat-b", 0.75), ("fine-pilot", 0.5)]:
        out = root / name
        out.mkdir(exist_ok=True)
        nodes, elements, _, _ = mesh_step(
            root / "geometry.step", g, MeshSettings(4, hotspot_size_mm=size), out
        )
        record = json.loads((out / "mesh-provenance.json").read_text(encoding="utf-8"))
        record.update(name=name, node_count=len(nodes), element_count=len(elements))
        records.append(record)
        print(name, len(nodes), len(elements), flush=True)
        (root / "pilot.json").write_text(
            json.dumps(records, indent=2), encoding="utf-8"
        )
    a, b = records[:2]
    report = dict(
        records=records,
        repeatable_coordinates=a["coordinates_sha256"] == b["coordinates_sha256"],
        repeatable_connectivity=a["topology_sha256"] == b["topology_sha256"],
        node_budget=250000,
        solver_timeout_s=600,
        note="Identical STEP used for repeatability; different refinement levels are independently remeshed, not nested.",
    )
    out = ROOT / "evidence/phase3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "mesh-pilot.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run()
