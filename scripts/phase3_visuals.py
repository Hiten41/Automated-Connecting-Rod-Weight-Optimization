"""Create traceable 3D figures directly from retained CalculiX fields."""

import json

import gmsh
import numpy as np
import plotly.graph_objects as go

from conrod.fea import ROOT
from conrod.visualization import actual_field_figure


def run():
    out = ROOT / "evidence/phase3"
    out.mkdir(parents=True, exist_ok=True)
    for mesh in ["0.35", "0.5"]:
        for kind in ["compression", "tension"]:
            case = ROOT / "runs/phase3-refinement" / f"{mesh}-{kind}"
            if not (case / "fields.json").exists():
                continue
            result = json.loads((case / "result.json").read_text(encoding="utf-8"))
            for field in ["stress", "displacement"]:
                fig = actual_field_figure(
                    case / "fields.json",
                    field,
                    deformation_scale=100 if field == "displacement" else 1,
                )
                fig.update_layout(
                    title=f"Phase3 {mesh}mm {kind}: actual {field}; CalculiX results; display decimation only"
                )
                fig.write_html(out / f"{mesh}-{kind}-{field}.html")
            (out / f"{mesh}-{kind}-figure-provenance.json").write_text(
                json.dumps(
                    dict(
                        fields_sha256=__import__("hashlib")
                        .sha256((case / "fields.json").read_bytes())
                        .hexdigest(),
                        mesh_sha256=json.loads(
                            (case / "mesh-provenance.json").read_text(encoding="utf-8")
                        )["mesh_sha256"],
                        result_sample_id=result["sample_id"],
                        stress_measure=result["stress_measure"],
                        units=dict(coordinates="mm", stress="MPa", displacement="mm"),
                        point_display="deterministically decimated; global maximum uses all solver values",
                    ),
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(mesh, kind, "figures complete", flush=True)

    case = ROOT / "runs/phase3-refinement/0.35-tension"
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.open(str(case / "mesh.msh"))
        tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = {
            int(tag): np.asarray(point, dtype=float)
            for tag, point in zip(tags, np.asarray(coordinates).reshape(-1, 3))
        }
        types, element_tags, connectivity = gmsh.model.mesh.getElements(3)
        if list(types) != [11]:
            raise ValueError(
                f"Expected quadratic tetrahedra (Gmsh type 11), got {types}"
            )
        elements = np.asarray(connectivity[0]).reshape(-1, 10)
    finally:
        gmsh.finalize()
    edges = set()
    for con in elements:
        corners = list(map(int, con[:4]))
        center = np.mean([nodes[n] for n in corners], axis=0)
        if 27 < center[0] < 34 and abs(center[1]) > 10:
            for i in range(4):
                for j in range(i):
                    edges.add(tuple(sorted((corners[i], corners[j]))))
    x = []
    y = []
    z = []
    for a, b in edges:
        x.extend([nodes[a][0], nodes[b][0], None])
        y.extend([nodes[a][1], nodes[b][1], None])
        z.extend([nodes[a][2], nodes[b][2], None])
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    peak = result["hotspot"]["coordinates_mm"]
    fig = go.Figure(
        go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode="lines",
            line=dict(color="#607d8b", width=1),
            name="Actual quadratic tetra corner edges",
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=[peak[0]],
            y=[peak[1]],
            z=[peak[2]],
            mode="markers",
            marker=dict(size=8, color="red"),
            name=f"Max IP: element {result['hotspot']['element_id']}, point {result['hotspot']['integration_point']}",
        )
    )
    fig.update_layout(
        title="0.35mm tension mesh: physical big-end transition ROI",
        scene=dict(
            aspectmode="data",
            xaxis_title="x mm",
            yaxis_title="y mm",
            zaxis_title="z mm",
        ),
    )
    fig.write_html(out / "0.35-tension-mesh-hotspot.html")


if __name__ == "__main__":
    run()
