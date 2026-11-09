from .schemas import Material

# Nominal project assumptions, not procurement/certification allowables.
MATERIALS = {
    "Forged Steel (AISI 4340)": Material(
        "Forged Steel (AISI 4340)", 205000.0, 0.29, 7.85e-6, 710.0
    ),
    "Titanium Alloy (Ti-6Al-4V)": Material(
        "Titanium Alloy (Ti-6Al-4V)", 113800.0, 0.34, 4.43e-6, 880.0
    ),
    "Forged Aluminum (7075-T6)": Material(
        "Forged Aluminum (7075-T6)", 71700.0, 0.33, 2.81e-6, 503.0
    ),
}


def mass_from_volume(volume_mm3, material):
    import math

    material.validate()
    if not math.isfinite(volume_mm3) or volume_mm3 <= 0:
        raise ValueError("Invalid volume")
    return volume_mm3 * material.density_kg_per_mm3
