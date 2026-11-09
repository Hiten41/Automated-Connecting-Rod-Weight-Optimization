"""C3D10 integration-point coordinates in CalculiX gauss3d5 order.
Source: https://github.com/Dhondtguido/CalculiX/blob/master/src/gauss.f
Quadratic shape mapping uses curved midside nodes, not tetra centroids.
"""

import numpy as np


def integration_coordinates(nodes, elements, stress):
    b = (5 - np.sqrt(5)) / 20
    a = 1 - 3 * b
    bary = np.full((4, 4), b)
    np.fill_diagonal(bary, a)
    N = np.concatenate(
        [
            bary * (2 * bary - 1),
            np.array(
                [
                    4 * bary[:, i] * bary[:, j]
                    for i, j in [(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)]
                ]
            ).T,
        ],
        axis=1,
    )
    mapped = {
        int(e): N @ np.array([nodes[n] if n in nodes else nodes[str(n)] for n in con])
        for e, con in elements.items()
    }
    if any(int(row[1]) not in (1, 2, 3, 4) for row in stress):
        raise ValueError("Expected four C3D10 integration points")
    return np.array([mapped[int(row[0])][int(row[1]) - 1] for row in stress])


def hotspot(nodes, elements, stress, g):
    from .fea import von_mises

    vm = von_mises(np.asarray(stress)[:, 2:])
    xyz = integration_coordinates(nodes, elements, stress)
    i = int(np.argmax(vm))
    p = xyz[i]
    if abs(np.linalg.norm(p[:2]) - g.big_end_id / 2) < 2:
        region = "big-end bore"
    elif abs(np.linalg.norm(p[:2] - [g.length_cc, 0]) - g.small_end_id / 2) < 2:
        region = "small-end bore"
    elif p[0] > g.length_cc - (g.small_end_id / 2 + 0.85 * g.ring_thickness) - 4:
        region = "small-end/shank transition"
    elif p[0] < g.big_end_id / 2 + g.ring_thickness + 4:
        region = "big-end/shank transition"
    else:
        region = "shank/pocket"
    local = np.linalg.norm(xyz - p, axis=1) <= 2
    return dict(
        element_id=int(stress[i][0]),
        integration_point=int(stress[i][1]),
        coordinates_mm=p.tolist(),
        region=region,
        location_type="quadratic C3D10 shape mapping, actual Gauss point",
        local_2mm_ip_mean_mpa=float(vm[local].mean()),
        local_2mm_point_count=int(local.sum()),
        local_measure_note="Unweighted descriptive IP mean within 2mm of moving peak, not an acceptance stress",
    )


def convergence(rows, tolerance=0.05):
    rows = sorted(
        [r for r in rows if r.get("status") == "FEA_SUCCESS"],
        key=lambda r: r["mesh"].get("hotspot_size_mm") or r["mesh"]["size_mm"],
        reverse=True,
    )
    if len(rows) < 3:
        return dict(status="INSUFFICIENT COMPUTE / VALIDATION", count=len(rows))
    keys = ["geometry", "material", "load"]
    if any(
        any(r[k] != rows[0][k] for k in keys)
        or r["mesh"]["boundary_mode"] != rows[0]["mesh"]["boundary_mode"]
        for r in rows
    ):
        raise ValueError(
            "Convergence requires identical geometry, material, loads and boundary conditions"
        )
    changes = {
        key: [abs(b[key] - a[key]) / abs(b[key]) for a, b in zip(rows, rows[1:])]
        for key in ["max_von_mises_mpa", "max_displacement_mm"]
    }
    passed = all(all(c < tolerance for c in v[-2:]) for v in changes.values())
    return dict(
        status="CONVERGED" if passed else "NOT CONVERGED",
        relative_changes=changes,
        tolerance=tolerance,
        mesh_sizes_mm=[
            r["mesh"].get("hotspot_size_mm") or r["mesh"]["size_mm"] for r in rows
        ],
        rule="Both peak stress and maximum displacement change <5% in two successive refinements; limited to this geometry/configuration",
    )
