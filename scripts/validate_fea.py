"""Independent axial patch test, bundled FreeCAD benchmark and refinement study."""

import argparse
import json
from pathlib import Path
import numpy as np
from conrod.fea import command, configuration, write_input, parse_dat, von_mises, solve
from conrod.schemas import Geometry, LoadCase, MeshSettings, Material
from conrod.materials import MATERIALS


def patch_test(out):
    import gmsh

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.occ.addBox(0, 0, 0, 100, 10, 10)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", 4)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.model.mesh.generate(3)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        nodes = {
            int(t): p.tolist() for t, p in zip(tags, np.array(coords).reshape(-1, 3))
        }
        types, ids, conn = gmsh.model.mesh.getElements(3)
        elements = {
            int(t): list(map(int, c[:8])) + [int(c[9]), int(c[8])]
            for t, c in zip(ids[0], np.array(conn[0]).reshape(-1, 10))
        }
        fixed = {n for n, p in nodes.items() if abs(p[0]) < 1e-8}
        weights = {}
        from conrod.fea import surface_weights

        for _, tag in gmsh.model.getEntities(2):
            if abs(gmsh.model.occ.getCenterOfMass(2, tag)[0] - 100) < 1e-7:
                _, _, c = gmsh.model.mesh.getElements(2, tag)
                weights = surface_weights(np.array(c[0]).reshape(-1, 6), nodes)
        gmsh.write(str(out / "bar.msh"))
    finally:
        gmsh.finalize()
    m = Material("Patch-test elastic solid", 200000, 0, 7.85e-6, 710)
    write_input(
        out / "bar.inp", nodes, elements, fixed, weights, m, LoadCase("tension", 1000)
    )
    command([configuration()["ccx"], "-i", "bar"], out, out / "solver.log")
    u, s = parse_dat(out / "bar.dat")
    delta = max(np.linalg.norm(p) for p in u.values())
    stress = float(max(von_mises(np.array(s)[:, 2:])))
    report = dict(
        expected_displacement_mm=0.005,
        actual_displacement_mm=delta,
        expected_stress_mpa=10.0,
        actual_stress_mpa=stress,
        passed=bool(abs(delta / 0.005 - 1) < 0.001 and abs(stress / 10 - 1) < 0.001),
        nodes=len(nodes),
        elements=len(elements),
    )
    (out / "report.json").write_text(json.dumps(report, indent=2))
    return report


def freecad_benchmark(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source = (
        Path(configuration()["freecad_python"]).parents[1]
        / "Mod/Fem/femtest/data/calculix/ccx_cantilever_faceload.inp"
    )
    text = source.read_text().replace(
        "*END STEP", "*NODE PRINT,NSET=Nall\nU\n*EL PRINT,ELSET=Eall\nS\n*END STEP"
    )
    (out / "benchmark.inp").write_text(text)
    log = command([configuration()["ccx"], "-i", "benchmark"], out, out / "solver.log")
    u, s = parse_dat(out / "benchmark.dat")
    report = dict(
        source=str(source),
        status="SUCCESS" if "Job finished" in log else "FAILED",
        displacement_nodes=len(u),
        stress_points=len(s),
        max_displacement_mm=max(float(np.linalg.norm(p)) for p in u.values()),
        scope="Bundled FreeCAD reference deck; solver/field smoke check, not an independent accuracy proof",
    )
    (out / "report.json").write_text(json.dumps(report, indent=2))
    return report


def refine(g, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for size in (6.0, 4.0, 2.5):
        for kind, force in [("compression", 28000.0), ("tension", 18000.0)]:
            r = solve(
                g,
                next(iter(MATERIALS.values())),
                LoadCase(kind, force),
                MeshSettings(size),
                out / f"{size}-{kind}",
            )
            results.append(r)
            print(size, kind, r["status"], flush=True)
    summary = []
    for kind in ("compression", "tension"):
        rr = [
            r
            for r in results
            if r["load"]["kind"] == kind and r["status"] == "FEA_SUCCESS"
        ]
        item = dict(
            load_case=kind,
            levels=[
                {
                    k: r[k]
                    for k in [
                        "mesh",
                        "node_count",
                        "element_count",
                        "max_von_mises_mpa",
                        "max_displacement_mm",
                        "runtime_s",
                    ]
                }
                for r in rr
            ],
        )
        if len(rr) == 3:
            item["last_refinement_change_pct"] = {
                k: 100 * abs(rr[-1][k] - rr[-2][k]) / rr[-1][k]
                for k in ["max_von_mises_mpa", "max_displacement_mm"]
            }
            item["provisional_5pct_target_met"] = all(
                v <= 5 for v in item["last_refinement_change_pct"].values()
            )
        summary.append(item)
    (out / "refinement.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="runs/validation")
    p.add_argument("--refine", action="store_true")
    p.add_argument("--geometry-json")
    a = p.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    if a.refine:
        g = (
            Geometry(**json.loads(Path(a.geometry_json).read_text()))
            if a.geometry_json
            else Geometry()
        )
        print(json.dumps(refine(g, out), indent=2))
    else:
        print(
            json.dumps(
                dict(
                    patch=patch_test(out / "patch"),
                    benchmark=freecad_benchmark(out / "benchmark"),
                ),
                indent=2,
            )
        )
