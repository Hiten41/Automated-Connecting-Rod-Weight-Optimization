"""Report measured results only; preserve raw peaks and fixed-region comparisons."""

import json
import gmsh
import numpy as np
from conrod.fea import ROOT
from conrod.fields import regional_stress_report, convergence
from conrod.schemas import Geometry
from conrod.visualization import convergence_figure


def run():
    rows = []
    for path in sorted((ROOT / "runs/phase3-refinement").glob("*/result.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        if r["status"] == "FEA_SUCCESS":
            f = json.loads((path.parent / "fields.json").read_text(encoding="utf-8"))
            report = regional_stress_report(
                f["nodes"],
                f["elements"],
                f["integration_point_stress"],
                Geometry(**r["geometry"]),
            )
            (path.parent / "regional-stress.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            r["regional_stress"] = report
            gmsh.initialize()
            try:
                gmsh.option.setNumber("General.Terminal", 0)
                gmsh.open(str(path.parent / "mesh.msh"))
                for region in report["regions"].values():
                    if region["count"]:
                        corners = f["elements"][str(region["element"])][:4]
                        vertices = np.asarray([f["nodes"][str(n)] for n in corners])
                        region["corner_edge_lengths_mm"] = [
                            float(np.linalg.norm(vertices[i] - vertices[j]))
                            for i in range(4)
                            for j in range(i)
                        ]
                        region["peak_element_minSICN"] = float(
                            gmsh.model.mesh.getElementQualities(
                                [region["element"]], "minSICN"
                            )[0]
                        )
            finally:
                gmsh.finalize()
        rows.append(r)
    out = ROOT / "evidence/phase3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "refinement-results.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    report = {
        k: convergence([r for r in rows if r["load"]["kind"] == k])
        for k in ["compression", "tension"]
    }
    report["method_limit"] = (
        "Independently generated nonnested meshes. No Richardson or GCI estimate for an unsuitable/nonmonotonic sequence. Local maxima supplement unaveraged global peak."
    )
    (out / "convergence.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    convergence_figure(rows).write_html(out / "convergence.html")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
