"""Recompute historical responses from preserved raw DAT and integration fields."""

import hashlib
import json

import numpy as np
import plotly.graph_objects as go
from conrod.fea import ROOT, parse_dat, von_mises
from conrod.fields import integration_coordinates


def run():
    source = ROOT.parent / "phase2-rod/runs/focused-refinement"
    output = ROOT / "evidence/phase3"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in sorted(source.glob("*-*")):
        if not (case / "fields.json").exists():
            continue
        result = json.loads((case / "result.json").read_text(encoding="utf-8"))
        fields = json.loads((case / "fields.json").read_text(encoding="utf-8"))
        u, stress = parse_dat(case / "job.dat")
        stress = np.asarray(stress)
        assert np.array_equal(stress, np.asarray(fields["integration_point_stress"]))
        vm = von_mises(stress[:, 2:])
        xyz = integration_coordinates(fields["nodes"], fields["elements"], stress)
        peak = int(vm.argmax())
        element = fields["elements"][str(int(stress[peak, 0]))]
        vertices = np.array([fields["nodes"][str(n)] for n in element[:4]])
        lengths = [
            float(np.linalg.norm(vertices[i] - vertices[j]))
            for i in range(4)
            for j in range(i)
        ]
        displacement = float(np.linalg.norm(list(u.values()), axis=1).max())
        assert np.isclose(vm[peak], result["max_von_mises_mpa"], rtol=1e-12)
        assert np.isclose(displacement, result["max_displacement_mm"], rtol=1e-12)
        row = dict(
            case=case.name,
            local_size_mm=result["mesh"]["hotspot_size_mm"],
            peak_mpa=float(vm[peak]),
            displacement_mm=displacement,
            xyz_mm=xyz[peak].tolist(),
            element=int(stress[peak, 0]),
            ip=int(stress[peak, 1]),
            components_mpa=stress[peak, 2:].tolist(),
            corner_edge_lengths_mm=lengths,
            historical_region=result["hotspot"]["region"],
            fields_sha256=hashlib.sha256(
                (case / "fields.json").read_bytes()
            ).hexdigest(),
            dat_sha256=hashlib.sha256((case / "job.dat").read_bytes()).hexdigest(),
        )
        rows.append(row)
        # Deterministic thinning for display only; retain hottest 200 actual samples.
        ids = np.unique(
            np.r_[
                np.arange(0, len(vm), max(1, len(vm) // 12000)), np.argsort(vm)[-200:]
            ]
        )
        fig = go.Figure(
            go.Scatter3d(
                x=xyz[ids, 0],
                y=xyz[ids, 1],
                z=xyz[ids, 2],
                mode="markers",
                marker=dict(
                    size=2,
                    color=vm[ids],
                    colorscale="Turbo",
                    colorbar=dict(title="MPa"),
                ),
                name="Actual unaveraged integration points",
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=[xyz[peak, 0]],
                y=[xyz[peak, 1]],
                z=[xyz[peak, 2]],
                mode="markers",
                marker=dict(size=7, color="black"),
                name=f"Peak E{row['element']} IP{row['ip']}",
            )
        )
        fig.update_layout(
            title=case.name + " — raw IP stress (display subsampled)",
            scene=dict(aspectmode="data"),
        )
        fig.write_html(output / (case.name + "-hotspots.html"))
    (output / "historical-field-audit.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    run()
