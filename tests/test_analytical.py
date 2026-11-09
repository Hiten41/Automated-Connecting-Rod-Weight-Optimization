from dataclasses import replace
import numpy as np
import pytest
from conrod.analytical import section, evaluate
from conrod.schemas import LoadCase


def test_section_independent_rectangle_decomposition(g):
    # Two side walls and horizontal middle web are disjoint rectangles.
    W, H, t, h = g.shank_width, g.beam_thickness, g.flange_thickness, g.web_thickness
    b = W - 2 * t
    s = section(g)
    assert s["area_mm2"] == pytest.approx(2 * t * H + b * h)
    assert s["I_y_mm4"] == pytest.approx(2 * t * H**3 / 12 + b * h**3 / 12)
    assert s["I_z_mm4"] == pytest.approx(
        2 * (H * t**3 / 12 + H * t * ((W - t) / 2) ** 2) + h * b**3 / 12
    )


def test_original_inertia_is_wrong(g):
    old = (
        2 * g.flange_thickness * g.shank_width**3 + g.web_thickness * g.pocket_width**3
    ) / 12
    assert not np.isclose(old, section(g)["I_z_mm4"])


def test_axial_hand_calculation(g, m):
    r = evaluate(g, m, LoadCase("tension", 28000))
    area = 25 * 22 - 2 * 2.2 * (25 - 11)
    assert r["estimated_nominal_stress_mpa"] == pytest.approx(28000 / area)
    assert r["estimated_displacement_mm"] == pytest.approx(
        28000 * 145 / (area * 205000)
    )
    assert r["estimated_factor_of_safety"] == pytest.approx(710 / (28000 / area))


def test_linear_scaling_and_direction(g, m):
    a = evaluate(g, m, LoadCase("tension", 20000))
    b = evaluate(g, m, LoadCase("compression", 40000))
    assert b["signed_axial_stress_mpa"] == pytest.approx(
        -2 * a["signed_axial_stress_mpa"]
    )
    assert b["estimated_displacement_mm"] == pytest.approx(
        2 * a["estimated_displacement_mm"]
    )
    assert evaluate(
        g,
        replace(m, youngs_modulus_mpa=2 * m.youngs_modulus_mpa),
        LoadCase("tension", 20000),
    )["estimated_displacement_mm"] == pytest.approx(a["estimated_displacement_mm"] / 2)


def test_buckling_rejected(g, m):
    r = evaluate(g, m, LoadCase("compression", 1e9))
    assert not r["valid"]
    assert r["buckling_margin"] < 1


def test_no_fake_mass_or_fea(g, m, load):
    r = evaluate(g, m, load)
    assert r["mass_kg"] is None
    assert "max_von_mises_mpa" not in r
