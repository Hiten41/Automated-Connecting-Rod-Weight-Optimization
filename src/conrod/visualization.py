import numpy as np
import plotly.graph_objects as go
import trimesh


def cad_figure(stl):
    mesh = trimesh.load(stl, force="mesh")
    v, f = mesh.vertices, mesh.faces
    fig = go.Figure(
        go.Mesh3d(
            x=v[:, 0],
            y=v[:, 1],
            z=v[:, 2],
            i=f[:, 0],
            j=f[:, 1],
            k=f[:, 2],
            color="#a9bacd",
            flatshading=False,
        )
    )
    fig.update_layout(
        scene=dict(
            aspectmode="data",
            xaxis_title="x / rod axis (mm)",
            yaxis_title="y / width (mm)",
            zaxis_title="z / thickness (mm)",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=480,
    )
    return fig


def nondominated(mass, stress):
    points = np.column_stack([mass, stress])
    keep = []
    for i, p in enumerate(points):
        keep.append(
            not np.any(np.all(points <= p, axis=1) & np.any(points < p, axis=1))
        )
    return np.array(keep)


def solver_field_figure(fields_path):
    """Actual integration-point VM, averaged per element and located at its centroid.
    Deliberately a point cloud rather than a falsely mapped surface contour.
    """
    import json
    from .fea import von_mises

    data = json.loads(__import__("pathlib").Path(fields_path).read_text())
    groups = {}
    for row in data["integration_point_stress"]:
        groups.setdefault(str(row[0]), []).append(float(von_mises(row[2:])))
    xyz = []
    values = []
    for eid, s in groups.items():
        c = data["elements"][eid][:4]
        xyz.append(np.mean([data["nodes"][str(n)] for n in c], axis=0))
        values.append(np.mean(s))
    xyz = np.array(xyz)
    fig = go.Figure(
        go.Scatter3d(
            x=xyz[:, 0],
            y=xyz[:, 1],
            z=xyz[:, 2],
            mode="markers",
            marker=dict(
                size=2,
                color=values,
                colorscale="Viridis",
                colorbar=dict(title="Mean VM (MPa)"),
            ),
        )
    )
    fig.update_layout(
        scene=dict(
            aspectmode="data",
            xaxis_title="x (mm)",
            yaxis_title="y (mm)",
            zaxis_title="z (mm)",
        ),
        height=450,
    )
    return fig
