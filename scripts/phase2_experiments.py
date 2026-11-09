"""Sequential bounded experiments; resume exact configuration only."""

import json
from conrod.fea import solve, ROOT
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS
from conrod.fields import convergence
from conrod.visualization import convergence_figure


def run_case(g, m, load, mesh, out):
    path = out / "result.json"
    if path.exists():
        old = json.loads(path.read_text())
        if (
            old.get("status") == "FEA_SUCCESS"
            and old["geometry"] == g.to_dict()
            and old["mesh"] == mesh.to_dict()
            and old["load"] == load.to_dict()
        ):
            return old
    print(str(out), flush=True)
    r = solve(g, m, load, mesh, out)
    print(r["status"], r.get("max_von_mises_mpa"), r.get("error"), flush=True)
    return r


def run():
    out = ROOT / "runs/phase2-experiments"
    out.mkdir(parents=True, exist_ok=True)
    g = Geometry()
    m = MATERIALS["Forged Steel (AISI 4340)"]
    rows = []
    for bc, sizes in [
        ("LEGACY_CLAMPED_BORE", [4.0]),
        ("COSINE_BEARING", [4.0, 2.5, 1.75, 1.25]),
    ]:
        for size in sizes:
            for kind, force in [("compression", 28000), ("tension", 18000)]:
                r = run_case(
                    g,
                    m,
                    LoadCase(kind, force),
                    MeshSettings(size, boundary_mode=bc),
                    out / f"{bc}-{size}-{kind}",
                )
                rows.append(r)
                (out / "results.json").write_text(json.dumps(rows, indent=2))
    selected = [r for r in rows if r["mesh"]["boundary_mode"] == "COSINE_BEARING"]
    report = {
        kind: convergence([r for r in selected if r["load"]["kind"] == kind])
        for kind in ["compression", "tension"]
    }
    (out / "convergence.json").write_text(json.dumps(report, indent=2))
    convergence_figure(selected).write_html(out / "convergence.html")
    print(report, flush=True)


if __name__ == "__main__":
    run()
