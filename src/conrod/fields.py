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

    def configuration(r):
        mesh = dict(r["mesh"])
        if mesh.get("hotspot_size_mm") is not None:
            mesh.pop("hotspot_size_mm", None)
        else:
            mesh.pop("size_mm", None)
        return mesh

    if any(
        any(r[k] != rows[0][k] for k in keys)
        or configuration(r) != configuration(rows[0])
        or r.get("simulation_version") != rows[0].get("simulation_version")
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


def regional_stress_report(nodes, elements, stress, g):
    """Fixed physical regions; no smoothing used for acceptance maxima.

    Element representative stress is von Mises of the arithmetic mean of its
    four integration-point tensors. It is descriptive, not a recovered peak.
    """
    from .fea import von_mises

    s = np.asarray(stress, dtype=float)
    xyz = integration_coordinates(nodes, elements, s)
    vm = von_mises(s[:, 2:])
    ids, inverse, counts = np.unique(
        s[:, 0].astype(int), return_inverse=True, return_counts=True
    )
    if not np.all(counts == 4) or len(np.unique(s[:, :2], axis=0)) != len(s):
        raise ValueError("Require exactly four unique integration points per element")
    tensors = np.zeros((len(ids), 6))
    np.add.at(tensors, inverse, s[:, 2:])
    tensors /= 4
    rb = g.big_end_id / 2 + g.ring_thickness
    rs = g.small_end_id / 2 + 0.85 * g.ring_thickness
    xb = np.sqrt(rb**2 - (g.shank_width / 2) ** 2)
    xs = g.length_cc - np.sqrt(rs**2 - (g.shank_width / 2) ** 2)
    regions = {
        "big_end_transition": (np.abs(xyz[:, 0] - xb) <= 2)
        & (np.abs(np.abs(xyz[:, 1]) - g.shank_width / 2) <= 2),
        "small_end_transition": (np.abs(xyz[:, 0] - xs) <= 2)
        & (np.abs(np.abs(xyz[:, 1]) - g.shank_width / 2) <= 2),
        "big_bore_2mm": np.abs(np.linalg.norm(xyz[:, :2], axis=1) - g.big_end_id / 2)
        <= 2,
        "small_bore_2mm": np.abs(
            np.linalg.norm(xyz[:, :2] - [g.length_cc, 0], axis=1) - g.small_end_id / 2
        )
        <= 2,
        "pocket_shank": (xyz[:, 0] >= rb + 2) & (xyz[:, 0] <= rb + 2 + g.pocket_length),
    }
    report = {}
    for name, mask in regions.items():
        selected = np.flatnonzero(mask)
        if not len(selected):
            report[name] = dict(count=0, status="UNSAMPLED")
            continue
        i = int(selected[np.argmax(vm[selected])])
        report[name] = dict(
            count=len(selected),
            peak_mpa=float(vm[i]),
            xyz_mm=xyz[i].tolist(),
            element=int(s[i, 0]),
            ip=int(s[i, 1]),
            components_mpa=s[i, 2:].tolist(),
        )
    return dict(
        raw_ip_peak_mpa=float(vm.max()),
        element_mean_tensor_vm_max_mpa=float(von_mises(tensors).max()),
        regions=report,
        nodal_extrapolation="NOT IMPLEMENTED; no extrapolated-stress claim",
        acceptance_measure="Maximum unaveraged IP stress; regional maxima supplement, never replace it",
        region_definition="Transitions: x within 2mm of nominal seam and |y| within 2mm of half-width, full thickness; bores: 2mm radial band; pocket: axial span",
    )
