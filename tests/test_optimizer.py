from conrod.optimizer import compliance, optimize
from conrod.schemas import Constraints, LoadCase, MeshSettings


class SafeFixture:
    def predict(self, g, m, load_case):
        return {"max_von_mises_mpa": 100.0, "max_displacement_mm": 0.01}


def test_missing_post_fea_rejected(g, m):
    ok, reasons, _ = compliance(g, m, [LoadCase()], [], Constraints())
    assert not ok


def test_failed_and_unsafe_fea_rejected(g, m):
    for r in [
        dict(status="FEA_FAILED"),
        dict(status="FEA_SUCCESS", max_von_mises_mpa=1000, max_displacement_mm=0.1),
    ]:
        assert not compliance(g, m, [LoadCase()], [r], Constraints())[0]


def test_no_invented_optimum(g, m, tmp_path):
    called = []

    def bad_solver(*a, **kw):
        called.append(a)
        return dict(status="FEA_FAILED")

    r = optimize(
        g,
        m,
        [LoadCase(), LoadCase("tension", 18000)],
        SafeFixture(),
        tmp_path,
        starts=1,
        mass_function=lambda g: g.ring_thickness * 0.01 + g.beam_thickness * 0.01,
        solver=bad_solver,
    )
    assert called
    assert r["status"] == "NO_VERIFIED_FEASIBLE_DESIGN"
    assert r["result"] is None
    assert r["global_search"]["method"] == "Differential Evolution"


def test_phase3_surrogate_requires_matching_mesh(g, m, tmp_path):
    trained_mesh = MeshSettings(
        4, hotspot_size_mm=0.75, refinement_region="big_end_transition"
    )
    phase3_model = type(
        "Phase3Model",
        (),
        {
            "metadata": {
                "model_version": "fea-3-deterministic-bearing-physics-scaled",
            "model_use": "ACCEPTED_FOR_OPTIMIZATION",
                "mesh_configuration": trained_mesh.to_dict(),
            }
        },
    )()
    try:
        optimize(
            g,
            m,
            [LoadCase("compression", 28000), LoadCase("tension", 18000)],
            phase3_model,
            tmp_path,
            mesh=MeshSettings(
                4, hotspot_size_mm=0.5, refinement_region="big_end_transition"
            ),
            mass_function=lambda _: 1.0,
        )
    except ValueError as exc:
        assert str(exc) == "Phase 3 surrogate and verification mesh differ"
    else:
        raise AssertionError("mismatched Phase 3 mesh was accepted")


def test_exploratory_phase3_surrogate_cannot_optimize(g, m, tmp_path):
    trained_mesh = MeshSettings(
        4, hotspot_size_mm=0.75, refinement_region="big_end_transition"
    )
    phase3_model = type(
        "Phase3Model",
        (),
        {
            "metadata": {
                "model_version": "fea-3-deterministic-bearing-physics-scaled",
                "model_use": "EXPLORATORY_SCREENING_ONLY",
                "mesh_configuration": trained_mesh.to_dict(),
            }
        },
    )()
    try:
        optimize(
            g,
            m,
            [LoadCase("compression", 28000), LoadCase("tension", 18000)],
            phase3_model,
            tmp_path,
            mesh=trained_mesh,
            mass_function=lambda _: 1.0,
        )
    except ValueError as exc:
        assert str(exc) == (
            "Phase 3 surrogate is exploratory only; held-out evidence does not authorize optimization"
        )
    else:
        raise AssertionError("screening-only Phase 3 surrogate was accepted")
