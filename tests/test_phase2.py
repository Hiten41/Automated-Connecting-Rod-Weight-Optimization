import numpy as np
import pytest
from dataclasses import replace
from conrod.schemas import Geometry, MeshSettings
from conrod.fields import integration_coordinates, convergence
from conrod.bearing import bearing_forces, rigid_body_gauges
from conrod.dataset import validate_record


def cylinder():
    nodes = {}
    tris = []

    def node(a, z):
        n = len(nodes) + 1
        nodes[n] = [25 * np.cos(a), 25 * np.sin(a), z]
        return n

    for a in np.linspace(0, 2 * np.pi, 49)[:-1]:
        b = a + 2 * np.pi / 48
        for z in range(0, 20, 2):
            # Two quadratic triangles per cylindrical angular-height cell.
            tris.append(
                [
                    node(a, z),
                    node(b, z),
                    node(b, z + 2),
                    node((a + b) / 2, z),
                    node(b, z + 1),
                    node((a + b) / 2, z + 1),
                ]
            )
            tris.append(
                [
                    node(a, z),
                    node(b, z + 2),
                    node(a, z + 2),
                    node((a + b) / 2, z + 1),
                    node((a + b) / 2, z + 2),
                    node(a, z + 1),
                ]
            )
    return nodes, tris


@pytest.mark.parametrize("force", [-28000, 18000])
def test_bearing_resultant_moment_and_nonnegative(force):
    nodes, tris = cylinder()
    forces, meta = bearing_forces(tris, nodes, [0, 0, 10], force)
    assert np.allclose(meta["resultant_n"], [force, 0, 0], atol=1e-7)
    assert np.linalg.norm(meta["moment_n_mm"]) < 1e-6
    assert meta["minimum_pressure_weight_n"] >= 0
    for n, f in forces.items():
        x, y, _ = nodes[n]
        assert np.dot(f, [x, y, 0]) >= 0
        assert x * np.sign(force) > -1e-8
    assert len(rigid_body_gauges(nodes, nodes, Geometry())) == 6


def test_quadratic_gauss_mapping():
    xyz = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ]
    )
    nodes = dict(enumerate(xyz, 1))
    elements = {10: list(nodes)}
    result = integration_coordinates(nodes, elements, [[10, i] for i in range(1, 5)])
    b = (5 - np.sqrt(5)) / 20
    a = 1 - 3 * b
    assert np.allclose(result, [[b, b, b], [a, b, b], [b, a, b], [b, b, a]])


def test_convergence_rejects_rising_peak_and_mixed_configuration():
    rows = [
        dict(
            status="FEA_SUCCESS",
            geometry={},
            material={},
            load={},
            mesh=MeshSettings(size).to_dict(),
            max_von_mises_mpa=s,
            max_displacement_mm=0.1,
        )
        for size, s in [(4, 280), (2.5, 320), (1.75, 360)]
    ]
    assert convergence(rows)["status"] == "NOT CONVERGED"
    rows[-1]["geometry"] = {"different": True}
    with pytest.raises(ValueError):
        convergence(rows)


def test_old_labels_excluded():
    with pytest.raises(ValueError, match="provenance"):
        validate_record({"geometry_version": "rod-1-sharp-pocket"})


def test_radius_and_boundary_validation():
    with pytest.raises(ValueError):
        replace(Geometry(), transition_radius_mm=3).validate()
    with pytest.raises(ValueError):
        MeshSettings(boundary_mode="contact").validate()


def test_physics_scaled_model_load_and_modulus_scaling():
    from conrod.surrogate import PhysicsScaledModel, FEATURES
    from sklearn.linear_model import Ridge

    X = np.ones((8, len(FEATURES)))
    X[:, FEATURES.index("force_n")] = np.arange(1, 9) * 1000
    X[:, FEATURES.index("youngs_modulus_mpa")] = 200000
    X[:, FEATURES.index("ring_thickness")] = np.linspace(5, 8, 8)
    scales = np.column_stack(
        [X[:, FEATURES.index("force_n")], X[:, FEATURES.index("force_n")] / 200000]
    )
    y = scales * np.column_stack(
        [
            0.01 + X[:, FEATURES.index("ring_thickness")] * 0.001,
            1 + X[:, FEATURES.index("ring_thickness")] * 0.01,
        ]
    )
    model = PhysicsScaledModel(Ridge()).fit(X, y)
    base = model.predict(X)
    doubled = X.copy()
    doubled[:, FEATURES.index("force_n")] *= 2
    assert np.allclose(model.predict(doubled), 2 * base)
    stiff = X.copy()
    stiff[:, FEATURES.index("youngs_modulus_mpa")] *= 2
    prediction = model.predict(stiff)
    assert np.allclose(prediction[:, 0], base[:, 0])
    assert np.allclose(prediction[:, 1], base[:, 1] / 2)


def test_reaction_audit_subtracts_applied_load(tmp_path):
    from conrod.bearing import equilibrium_audit

    deck = tmp_path / "job.inp"
    dat = tmp_path / "job.dat"
    deck.write_text("*CLOAD\n1,1,10\n2,1,-10\n*END STEP\n")
    dat.write_text(" forces (fx,fy,fz)\n1 10 0 0\n2 -10 0 0\n")
    audit = equilibrium_audit(deck, dat, {1: [0, 0, 0], 2: [1, 0, 0]}, [(1, 1)], 10)
    assert audit["reaction_total_n"] == [0, 0, 0]
    assert audit["force_balance_fraction"] == 0
