from conrod.optimizer import compliance, optimize
from conrod.schemas import Constraints, LoadCase


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
