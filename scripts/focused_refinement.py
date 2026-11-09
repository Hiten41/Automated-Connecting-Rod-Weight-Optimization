import json
from conrod.fea import ROOT
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS
from conrod.fields import convergence
from conrod.visualization import convergence_figure
from phase2_experiments import run_case


def run():
    rows = []
    out = ROOT / "runs/focused-refinement"
    out.mkdir(exist_ok=True)
    for local in [1.75, 1.25, 1.0, 0.75]:
        for kind, force in [("compression", 28000), ("tension", 18000)]:
            r = run_case(
                Geometry(),
                MATERIALS["Forged Steel (AISI 4340)"],
                LoadCase(kind, force),
                MeshSettings(4, hotspot_size_mm=local),
                out / f"{local}-{kind}",
            )
            rows.append(r)
            (out / "results.json").write_text(json.dumps(rows, indent=2))
    report = {
        kind: convergence([r for r in rows if r["load"]["kind"] == kind])
        for kind in ["compression", "tension"]
    }
    (out / "convergence.json").write_text(json.dumps(report, indent=2))
    convergence_figure(rows).write_html(out / "convergence.html")
    print(report, flush=True)


if __name__ == "__main__":
    run()
