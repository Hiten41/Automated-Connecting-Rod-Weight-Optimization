"""Compressive cosine bearing pressure, self-equilibrated bore forces, six gauges."""

import numpy as np


def bearing_forces(triangles, nodes, center, force):
    from .fea import surface_weights

    weights = surface_weights(triangles, nodes)
    ids = np.array(list(weights))
    xyz = np.array([nodes[int(n)] for n in ids]) - np.array(center)
    radial = xyz.copy()
    radial[:, 2] = 0
    radial /= np.linalg.norm(radial, axis=1)[:, None]
    base = np.array(list(weights.values())) * np.maximum(
        np.sign(force) * radial[:, 0], 0
    )
    active = base > 0
    ids, xyz, radial, base = ids[active], xyz[active], radial[active], base[active]
    base *= abs(force) / abs(np.sum(base * radial[:, 0]))
    moment = np.cross(xyz, radial)
    A = np.array([radial[:, 0], radial[:, 1], moment[:, 0], moment[:, 1]])
    target = np.array([force, 0.0, 0.0, 0.0])
    # Minimum relative correction to discrete pressure weights to integrate exact
    # force and zero torque. Remains radial and compressive; reject negative values.
    correction = A.T @ np.linalg.solve((A * base) @ A.T, target - A @ base)
    corrected = base * (1 + correction)
    if np.min(corrected) < -1e-9 or np.max(abs(correction)) > 0.25:
        raise ValueError("Bearing quadrature correction invalid; refine mesh")
    f = corrected[:, None] * radial
    return {int(n): v.tolist() for n, v in zip(ids, f)}, dict(
        resultant_n=f.sum(axis=0).tolist(),
        moment_n_mm=np.cross(xyz, f).sum(axis=0).tolist(),
        max_relative_quadrature_correction=float(max(abs(correction))),
        minimum_pressure_weight_n=float(min(corrected)),
        loaded_node_count=len(ids),
    )


def rigid_body_gauges(ids, nodes, g):
    ids = sorted(ids)
    xyz = np.array([nodes[n] for n in ids])
    R = g.big_end_id / 2
    targets = [[0, -R, 0], [0, R, 0], [0, -R, g.beam_thickness]]
    picked = [
        ids[int(np.argmin(np.linalg.norm(xyz - np.array(t), axis=1)))] for t in targets
    ]
    constraints = [
        (picked[0], 1),
        (picked[0], 2),
        (picked[0], 3),
        (picked[1], 1),
        (picked[1], 3),
        (picked[2], 1),
    ]
    rows = []
    for n, d in constraints:
        x, y, z = nodes[n]
        B = np.array([[1, 0, 0, 0, z, -y], [0, 1, 0, -z, 0, x], [0, 0, 1, y, -x, 0]])
        rows.append(B[d - 1])
    if np.linalg.matrix_rank(rows) != 6:
        raise ValueError("Rigid body gauge is rank deficient")
    return constraints


def write_bearing_input(path, nodes, elements, surfaces, g, m, load):
    from .fea import write_input

    fixed = {n for t in surfaces["fixed"] for n in t}
    gauges = rigid_body_gauges(fixed, nodes, g)
    small, sm = bearing_forces(
        surfaces["loaded"],
        nodes,
        [g.length_cc, 0, g.beam_thickness / 2],
        load.signed_force,
    )
    big, bg = bearing_forces(
        surfaces["fixed"], nodes, [0, 0, g.beam_thickness / 2], -load.signed_force
    )
    forces = {**small, **big}
    write_input(path, nodes, elements, [], {}, m, load)
    text = path.read_text().replace(
        "*BOUNDARY\n", "*BOUNDARY\n" + "".join(f"{n},{d},{d}\n" for n, d in gauges)
    )
    text = text.replace(
        "*CLOAD\n",
        "*CLOAD\n"
        + "".join(
            f"{n},{d + 1},{v:.10e}\n"
            for n, f in forces.items()
            for d, v in enumerate(f)
            if abs(v) > 1e-12
        ),
    )
    path.write_text(text)
    return dict(
        model="COSINE_BEARING",
        resultant_n=sm["resultant_n"],
        opposite_bore=bg,
        loaded_bore=sm,
        total_applied_n=(np.array(sm["resultant_n"]) + bg["resultant_n"]).tolist(),
        gauges=gauges,
        pressure="q proportional to max(sign(F)*nx,0); radial outward from bore center",
        limitations="Prescribed frictionless pressure approximation; no pin contact solution; six rigid-body gauge DOFs",
    )


def reaction_forces(path):
    state = False
    result = {}
    for line in path.read_text().splitlines():
        low = line.strip().lower()
        if low.startswith("forces"):
            state = True
            continue
        if low.startswith(("stresses", "displacements")):
            state = False
        parts = line.split()
        if state and len(parts) == 4 and parts[0].isdigit():
            result[int(parts[0])] = [float(v.replace("D", "E")) for v in parts[1:]]
    if not result:
        raise ValueError("Missing reaction output")
    return result


def equilibrium_audit(deck, dat, nodes, gauges, force_scale):
    """RF is applied load + reaction (CCX manual); subtract actual deck CLOADs."""
    applied = {}
    active = False
    for line in deck.read_text().splitlines():
        if line.startswith("*"):
            active = line.upper().startswith("*CLOAD")
            continue
        if active and line.strip():
            n, d, value = line.split(",")
            applied.setdefault(int(n), np.zeros(3))[int(d) - 1] += float(value)
    rf = reaction_forces(dat)
    reaction = {}
    for n, d in gauges:
        reaction.setdefault(n, np.zeros(3))[d - 1] = (
            rf[n][d - 1] - applied.get(n, np.zeros(3))[d - 1]
        )
    load_sum = np.sum(list(applied.values()), axis=0)
    reaction_sum = np.sum(list(reaction.values()), axis=0)
    moment = np.zeros(3)
    for table in [applied, reaction]:
        for n, f in table.items():
            xyz = nodes[n] if n in nodes else nodes[str(n)]
            moment += np.cross(xyz, f)
    return dict(
        applied_total_n=load_sum.tolist(),
        reaction_total_n=reaction_sum.tolist(),
        balance_residual_n=(load_sum + reaction_sum).tolist(),
        balance_moment_n_mm=moment.tolist(),
        reaction_dof_norm_fraction=float(
            np.linalg.norm(list(reaction.values())) / force_scale
        ),
        force_balance_fraction=float(
            np.linalg.norm(load_sum + reaction_sum) / force_scale
        ),
        interpretation="RF minus actual CLOAD at each constrained DOF; no DLOAD or MPC in bearing model",
    )
