"""Uniform shank estimates; not bore peaks or FEA stresses.
Global x is the rod axis, y width W, z thickness H. Iy is integral z^2 dA;
Iz is integral y^2 dA. Both Euler effective-length factors default to 1.
"""

import math
from .materials import mass_from_volume
from .schemas import Geometry, Material, LoadCase, AnalyticalResult


def section(g):
    g.validate()
    W, H, d, b = g.shank_width, g.beam_thickness, g.pocket_depth, g.pocket_width
    area = W * H - 2 * d * b
    iy = W * H**3 / 12 - 2 * (b * d**3 / 12 + b * d * ((H - d) / 2) ** 2)
    iz = (H * W**3 - 2 * d * b**3) / 12
    return dict(area_mm2=area, I_y_mm4=iy, I_z_mm4=iz)


def evaluate(
    g: Geometry,
    m: Material,
    load: LoadCase,
    volume_mm3=None,
    effective_length_factor=1.0,
) -> AnalyticalResult:
    g.validate()
    m.validate()
    load.validate()
    if not math.isfinite(effective_length_factor) or effective_length_factor <= 0:
        raise ValueError("Invalid K")
    s = section(g)
    pcr = (
        math.pi**2
        * m.youngs_modulus_mpa
        * min(s["I_y_mm4"], s["I_z_mm4"])
        / (effective_length_factor * g.length_cc) ** 2
    )
    stress = load.force_n / s["area_mm2"]
    margin = pcr / load.force_n if load.kind == "compression" else None
    stable = margin is None or margin > 1
    return dict(
        status="ANALYTICAL",
        estimated_nominal_stress_mpa=stress,
        signed_axial_stress_mpa=load.signed_force / s["area_mm2"],
        estimated_displacement_mm=load.force_n
        * g.length_cc
        / (s["area_mm2"] * m.youngs_modulus_mpa),
        estimated_factor_of_safety=m.yield_strength_mpa / stress,
        euler_critical_load_n=pcr,
        buckling_margin=margin,
        valid=stable,
        mass_kg=mass_from_volume(volume_mm3, m) if volume_mm3 is not None else None,
        mass_source="CAD" if volume_mm3 is not None else "unavailable",
        assumptions=[
            "Uniform shank over center distance; excludes bore compliance and stress concentrations",
            "Pinned-pinned Euler screen, not nonlinear buckling analysis",
            "Invalid compression above Euler limit",
        ],
        **s,
    )
