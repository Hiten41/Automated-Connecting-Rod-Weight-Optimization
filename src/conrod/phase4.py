"""Physics-guided screening and constraint bookkeeping for Phase 4.

Screening values never substitute for the actual CalculiX fields.  A design is
not called feasible until both load cases and a compression buckling result are
present and satisfy the project constraints.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Phase4Constraints:
    minimum_factor_of_safety: float = 1.8
    maximum_displacement_mm: float = 0.35
    minimum_buckling_factor: float = 1.8

    @property
    def allowable_stress_mpa(self):
        return 710.0 / self.minimum_factor_of_safety

    def to_dict(self):
        return asdict(self) | {"allowable_stress_mpa": self.allowable_stress_mpa}


def assess_candidate(
    load_results,
    buckling_factor=None,
    independent_refined=False,
    constraints=Phase4Constraints(),
):
    """Assess actual FEA outputs without promoting coarse screens to feasibility."""
    reasons = []
    if set(load_results) != {"compression", "tension"}:
        reasons.append("BOTH_LOAD_CASES_REQUIRED")
    stress_values = []
    displacement_values = []
    for kind in ("compression", "tension"):
        result = load_results.get(kind, {})
        if result.get("status") != "FEA_SUCCESS":
            reasons.append(f"{kind.upper()}_FEA_NOT_SUCCESSFUL")
            continue
        stress = result.get("max_von_mises_mpa")
        displacement = result.get("max_displacement_mm")
        if stress is None or displacement is None:
            reasons.append(f"{kind.upper()}_FIELDS_MISSING")
            continue
        stress_values.append(float(stress))
        displacement_values.append(float(displacement))
        if float(stress) > constraints.allowable_stress_mpa:
            reasons.append(f"{kind.upper()}_STRESS_EXCEEDS_ALLOWABLE")
        if float(displacement) > constraints.maximum_displacement_mm:
            reasons.append(f"{kind.upper()}_DISPLACEMENT_EXCEEDS_LIMIT")
    if buckling_factor is None:
        reasons.append("BUCKLING_NOT_VERIFIED")
    elif buckling_factor < constraints.minimum_buckling_factor:
        reasons.append("BUCKLING_FACTOR_BELOW_LIMIT")
    if not independent_refined:
        reasons.append("REFINED_INDEPENDENT_VERIFICATION_REQUIRED")
    return {
        "feasibility_status": "FEASIBLE" if not reasons else "NOT_FEASIBLE_OR_UNVERIFIED",
        "constraints": constraints.to_dict(),
        "maximum_stress_mpa": max(stress_values) if stress_values else None,
        "maximum_displacement_mm": max(displacement_values) if displacement_values else None,
        "minimum_factor_of_safety": (
            710.0 / max(stress_values) if stress_values else None
        ),
        "linear_buckling_factor": buckling_factor,
        "reasons": reasons,
        "feasibility_note": (
            "Coarse-mesh screens are not eligible for FEASIBLE status; provide "
            "the refined independent verification and buckling factor."
        ),
    }


def objective_mass(mass_kg, assessment):
    """Mass may be optimized only after all structural constraints pass."""
    if assessment.get("feasibility_status") != "FEASIBLE":
        raise ValueError("Mass objective is disabled until structural feasibility is verified")
    if mass_kg <= 0:
        raise ValueError("Mass must be positive")
    return float(mass_kg)
