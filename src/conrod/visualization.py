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


def actual_field_figure(fields_path, kind="stress", deformation_scale=1.0):
    """Unaveraged IP stresses or actual nodal U; no stress extrapolation."""

    import json

    from pathlib import Path

    from .fields import integration_coordinates

    from .fea import von_mises

    d = json.loads(Path(fields_path).read_text())

    if kind == "stress":
        xyz = integration_coordinates(
            d["nodes"], d["elements"], d["integration_point_stress"]
        )

        values = von_mises(np.asarray(d["integration_point_stress"])[:, 2:])

        label = "Unaveraged IP VM (MPa)"

    else:
        ids = list(d["nodes"])
        xyz = np.array([d["nodes"][n] for n in ids])

        u = np.array([d["displacement"][n] for n in ids])
        xyz += deformation_scale * u

        values = np.linalg.norm(u, axis=1)
        label = f"Nodal U (mm); deformation ×{deformation_scale:g}"

    peak = int(np.argmax(values))

    # Deterministic display decimation only. Scalar maximum and marked peak use ALL data.

    idx = np.unique(
        np.r_[np.arange(0, len(values), max(1, len(values) // 40000)), peak]
    )

    fig = go.Figure(
        go.Scatter3d(
            x=xyz[idx, 0],
            y=xyz[idx, 1],
            z=xyz[idx, 2],
            mode="markers",
            marker=dict(
                size=2,
                color=values[idx],
                colorscale="Turbo",
                colorbar=dict(title=label),
            ),
            name=label,
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=[xyz[peak, 0]],
            y=[xyz[peak, 1]],
            z=[xyz[peak, 2]],
            mode="markers",
            marker=dict(size=7, color="red", symbol="diamond"),
            name=f"Max {values[peak]:.3f}",
        )
    )

    fig.update_layout(
        height=550,
        scene=dict(
            aspectmode="data",
            xaxis_title="x (mm)",
            yaxis_title="y (mm)",
            zaxis_title="z (mm)",
        ),
        margin=dict(l=0, r=0, t=25, b=0),
    )

    return fig


def convergence_figure(rows):

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["Peak unaveraged stress", "Maximum displacement"],
    )

    for kind in ["compression", "tension"]:
        data = sorted(
            [
                r
                for r in rows
                if r.get("status") == "FEA_SUCCESS" and r["load"]["kind"] == kind
            ],
            key=lambda r: r["mesh"]["size_mm"],
        )

        for col, key in [(1, "max_von_mises_mpa"), (2, "max_displacement_mm")]:
            fig.add_trace(
                go.Scatter(
                    x=[
                        r["mesh"].get("hotspot_size_mm") or r["mesh"]["size_mm"]
                        for r in data
                    ],
                    y=[r[key] for r in data],
                    mode="lines+markers",
                    name=kind,
                    legendgroup=kind,
                    showlegend=col == 1,
                ),
                row=1,
                col=col,
            )

    fig.update_xaxes(
        title_text="Refinement size (mm; local when configured)", autorange="reversed"
    )

    fig.update_yaxes(title_text="MPa", row=1, col=1)
    fig.update_yaxes(title_text="mm", row=1, col=2)

    return fig
