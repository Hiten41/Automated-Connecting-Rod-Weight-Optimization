"""Reproducible Latin-hypercube candidate generation and constraint ranking."""

from __future__ import annotations

from collections import defaultdict

from scipy.stats import qmc

from .design_families import FAMILIES, FamilyDesign
from .phase4 import Phase4Constraints


def lhs_designs(family: str, count: int, seed: int = 20261110) -> list[FamilyDesign]:
    """Create a seeded LHS sample for one family in the documented bounds.

    The first ten coordinates vary shared structural and pocket/rib parameters;
    tapered designs use three additional coordinates for their station widths.
    Some bounds depend on sampled variables to preserve basic section geometry.
    CAD validity is still determined by FreeCAD, not by this parameter sampler.
    """
    if family not in FAMILIES:
        raise ValueError(f"Unknown design family: {family}")
    if count < 1:
        raise ValueError("count must be positive")
    dim = 13 if family == "tapered" else 10
    sampler = qmc.LatinHypercube(d=dim, seed=int(seed))
    points = sampler.random(int(count))
    designs = []
    for u in points:
        ring = 6.2 + 4.3 * u[0]
        width = 26.0 + 14.0 * u[1]
        depth = 23.0 + 11.0 * u[2]
        flange_hi = min(8.0, (depth - 4.5) / 2)
        flange = 4.0 + (flange_hi - 4.0) * u[3]
        web_hi = min(7.5, width - 8.0)
        web = 3.5 + (web_hi - 3.5) * u[4]
        radius_hi = min(3.8, ring / 2 - 0.1, flange - 0.1)
        radius = 0.8 + (radius_hi - 0.8) * u[5]
        values = {
            "family": family,
            "ring_thickness": ring,
            "shank_width": width,
            "beam_thickness": depth,
            "flange_thickness_mm": flange,
            "web_thickness_mm": web,
            "transition_radius_mm": radius,
            "pocket_length_mm": 15.0 + 31.0 * u[6],
            "pocket_width_mm": 8.0 + (min(16.0, width - 2 * flange - 2.0) - 8.0) * u[7],
            "rib_height_mm": 1.5 + 4.0 * u[8],
            "rib_length_mm": 10.0 + 22.0 * u[9],
        }
        if family == "tapered":
            big_lo, big_hi = max(28.0, web + 7.0), min(43.0, width + 5.0)
            big = big_lo + (big_hi - big_lo) * u[10]
            mid_lo = max(25.0, web + 7.0)
            mid = mid_lo + (big - mid_lo) * u[11]
            small_lo = max(22.0, web + 7.0)
            small = small_lo + (mid - small_lo) * u[12]
            values.update(
                shank_width=big,
                taper_big_width_mm=big,
                taper_mid_width_mm=mid,
                taper_small_width_mm=small,
            )
        designs.append(FamilyDesign(**values))
    return designs


def mass_stratified_candidates(candidates, per_family: int = 3):
    """Return low/mid/high actual-mass candidates from each family."""
    grouped = defaultdict(list)
    for row in candidates:
        if (
            row.get("status") == "CAD_VALID"
            and row.get("actual_cad_mass_g") is not None
        ):
            grouped[row["family"]].append(row)
    selected = []
    for family in FAMILIES:
        rows = sorted(grouped[family], key=lambda r: r["actual_cad_mass_g"])
        if not rows:
            continue
        n = min(int(per_family), len(rows))
        indexes = sorted({round(i * (len(rows) - 1) / max(n - 1, 1)) for i in range(n)})
        selected.extend(rows[i] for i in indexes)
    return selected


def normalized_constraint_margins(
    compression_stress_mpa: float,
    tension_stress_mpa: float,
    max_displacement_mm: float,
    buckling_factor: float | None,
    constraints: Phase4Constraints | None = None,
):
    """Compute normalized nonnegative margins for the project constraints."""
    constraints = constraints or Phase4Constraints()
    allow = constraints.allowable_stress_mpa
    return {
        "compression_stress": (allow - compression_stress_mpa) / allow,
        "tension_stress": (allow - tension_stress_mpa) / allow,
        "displacement": (constraints.maximum_displacement_mm - max_displacement_mm)
        / constraints.maximum_displacement_mm,
        "buckling": None
        if buckling_factor is None
        else (buckling_factor - constraints.minimum_buckling_factor)
        / constraints.minimum_buckling_factor,
    }


def rank_recorded_screen_passes(candidates):
    """Sort recorded numerical screen passes by actual CAD mass.

    This is a finite-study ranking helper. It does not certify candidates or
    make them eligible for a mechanical optimization objective.
    """
    return sorted(
        (
            row
            for row in candidates
            if row.get("assessment", {}).get("recorded_screen_status") == "PASS"
        ),
        key=lambda row: row["actual_cad_mass_g"],
    )


def rank_verified_feasible(candidates):
    """Deprecated compatibility alias; results are recorded-screen passes only."""
    return rank_recorded_screen_passes(candidates)
