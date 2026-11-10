"""Phase 4 recorded-screen assessment and evidence status helpers.

These statuses describe the supplied CalculiX results only. A numerical screen
pass is not independent solver verification or mechanical qualification.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import isfinite


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


def ordered_mesh_levels(levels):
    """Return unique positive mesh targets, ordered coarse to fine."""
    normalized = []
    seen = set()
    for level in levels:
        try:
            numeric = float(level)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Mesh target must be numeric: {level!r}") from exc
        if not isfinite(numeric) or numeric <= 0:
            raise ValueError(f"Mesh target must be finite and positive: {level!r}")
        if numeric in seen:
            raise ValueError(f"Duplicate numeric mesh target: {level!r}")
        seen.add(numeric)
        normalized.append((numeric, str(level)))
    return tuple(label for _, label in sorted(normalized, reverse=True))


def _finite_nonnegative(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) and number >= 0 else None


def _successful_static_pair(cases):
    if not isinstance(cases, Mapping) or not {"compression", "tension"}.issubset(cases):
        return False
    for kind in ("compression", "tension"):
        result = cases.get(kind)
        if not isinstance(result, Mapping) or result.get("status") != "FEA_SUCCESS":
            return False
        if _finite_nonnegative(result.get("max_von_mises_mpa")) is None:
            return False
        if _finite_nonnegative(result.get("max_displacement_mm")) is None:
            return False
    return True


def finest_successful_mesh_level(results_by_level):
    """Select the finest configured mesh with successful compression and tension."""
    if not isinstance(results_by_level, Mapping) or not results_by_level:
        return None
    levels = ordered_mesh_levels(results_by_level)
    successful = [
        level for level in levels if _successful_static_pair(results_by_level[level])
    ]
    return successful[-1] if successful else None


def static_pair_passes(results, allowable_stress_mpa, maximum_displacement_mm):
    """Check both FEA load cases without allowing missing or nonfinite values."""
    if not _successful_static_pair(results):
        return False
    for kind in ("compression", "tension"):
        case = results[kind]
        stress = _finite_nonnegative(case.get("max_von_mises_mpa"))
        displacement = _finite_nonnegative(case.get("max_displacement_mm"))
        if stress is None or displacement is None:
            return False
        if stress > allowable_stress_mpa or displacement > maximum_displacement_mm:
            return False
    return True


def mesh_refinement_summary(results_by_level, stress_limit_percent=5.0):
    """Assess only the last adjacent coarse-to-fine target pair.

    The targets are nonnested; a PASS is only a successive peak-stress trend
    screen and does not establish continuum convergence or a GCI.
    """
    levels = ordered_mesh_levels(results_by_level) if results_by_level else ()
    output = {
        "status": "UNVERIFIED",
        "pair_levels_mm": None,
        "stress_change_percent": {},
        "displacement_change_percent": {},
        "maximum_peak_stress_change_percent": None,
        "interpretation": "CONTINUUM_MESH_ERROR_NOT_ESTABLISHED",
    }
    if len(levels) < 2:
        output["reason"] = "TWO_SUCCESSIVE_MESH_LEVELS_REQUIRED"
        return output

    coarser_level, finer_level = levels[-2:]
    coarser = results_by_level[coarser_level]
    finer = results_by_level[finer_level]
    output["pair_levels_mm"] = [float(coarser_level), float(finer_level)]
    if not _successful_static_pair(coarser) or not _successful_static_pair(finer):
        output["reason"] = "LAST_SUCCESSIVE_PAIR_INCOMPLETE_OR_FAILED"
        return output

    for kind in ("compression", "tension"):
        output["stress_change_percent"][kind] = {}
        output["displacement_change_percent"][kind] = {}
        for field, target in (
            ("max_von_mises_mpa", "stress_change_percent"),
            ("max_displacement_mm", "displacement_change_percent"),
        ):
            coarse_value = _finite_nonnegative(coarser[kind].get(field))
            fine_value = _finite_nonnegative(finer[kind].get(field))
            if coarse_value is None or fine_value is None or coarse_value == 0:
                output["status"] = "UNVERIFIED"
                output["reason"] = "MESH_TREND_VALUE_MISSING_OR_INVALID"
                return output
            output[target][kind] = (
                100.0 * abs(fine_value - coarse_value) / abs(coarse_value)
            )

    maximum = max(
        output["stress_change_percent"][kind] for kind in ("compression", "tension")
    )
    output["maximum_peak_stress_change_percent"] = maximum
    output["status"] = "PASS" if maximum < stress_limit_percent else "FAIL"
    output["reason"] = (
        "SUCCESSIVE_NONNESTED_STRESS_CHANGE_BELOW_LIMIT"
        if output["status"] == "PASS"
        else "SUCCESSIVE_STRESS_CHANGE_AT_OR_ABOVE_LIMIT"
    )
    return output


def _normalized_cad_status(value):
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    if isinstance(value, str):
        if value in {"PASS", "CAD_VALID", "VALID"}:
            return "PASS"
        if value in {"FAIL", "CAD_INVALID", "INVALID"}:
            return "FAIL"
    return "UNVERIFIED"


def assess_candidate(
    load_results,
    buckling_factor=None,
    constraints=None,
    *,
    cad_validity_status="UNVERIFIED",
    mesh_refinement_status="UNVERIFIED",
    buckling_mesh_matches=False,
    finest_mesh_level_mm=None,
):
    """Assess recorded FEA screens without promoting them to qualification."""
    constraints = constraints or Phase4Constraints()
    reasons = []
    required_cases = {"compression", "tension"}
    if not isinstance(load_results, Mapping):
        load_results = {}
    if set(load_results) != required_cases:
        reasons.append("BOTH_LOAD_CASES_REQUIRED")

    stress_values = []
    displacement_values = []
    case_success = {}
    static_failures = []
    for kind in ("compression", "tension"):
        result = load_results.get(kind, {})
        result = result if isinstance(result, Mapping) else {}
        successful = result.get("status") == "FEA_SUCCESS"
        case_success[kind] = successful
        if not successful:
            reasons.append(f"{kind.upper()}_FEA_NOT_SUCCESSFUL")
            continue

        stress = _finite_nonnegative(result.get("max_von_mises_mpa"))
        displacement = _finite_nonnegative(result.get("max_displacement_mm"))
        if stress is None or displacement is None:
            reasons.append(f"{kind.upper()}_FIELDS_MISSING_OR_INVALID")
            case_success[kind] = False
            continue
        stress_values.append(stress)
        displacement_values.append(displacement)
        if stress > constraints.allowable_stress_mpa:
            static_failures.append(f"{kind.upper()}_STRESS_EXCEEDS_ALLOWABLE")
        if displacement > constraints.maximum_displacement_mm:
            static_failures.append(f"{kind.upper()}_DISPLACEMENT_EXCEEDS_LIMIT")
    if static_failures:
        reasons.extend(static_failures)

    static_complete = (
        all(case_success.values())
        and len(stress_values) == 2
        and len(displacement_values) == 2
    )
    fea_execution_status = (
        "PASS"
        if static_complete
        else "FAIL"
        if any(not value for value in case_success.values())
        else "UNVERIFIED"
    )

    buckling_value = _finite_nonnegative(buckling_factor)
    if buckling_value is None or buckling_value <= 0:
        reasons.append("POSITIVE_BUCKLING_FACTOR_MISSING_OR_INVALID")
        buckling_screen_status = "UNVERIFIED"
    elif not buckling_mesh_matches:
        reasons.append("BUCKLING_MESH_ASSOCIATION_MISMATCH")
        buckling_screen_status = "UNVERIFIED"
    elif buckling_value < constraints.minimum_buckling_factor:
        reasons.append("BUCKLING_FACTOR_BELOW_LIMIT")
        buckling_screen_status = "FAIL"
    else:
        buckling_screen_status = "PASS"

    cad_status = _normalized_cad_status(cad_validity_status)
    if cad_status == "FAIL":
        reasons.append("CAD_VALIDATION_FAILED")
    elif cad_status == "UNVERIFIED":
        reasons.append("CAD_VALIDATION_NOT_RECORDED")

    if not buckling_mesh_matches:
        reasons.append("BUCKLING_MESH_ASSOCIATION_NOT_VERIFIED")
    if not static_complete:
        recorded_screen_status = "UNVERIFIED"
    elif static_failures or buckling_screen_status == "FAIL" or cad_status == "FAIL":
        recorded_screen_status = "FAIL"
    elif buckling_screen_status != "PASS" or cad_status != "PASS":
        recorded_screen_status = "UNVERIFIED"
    else:
        recorded_screen_status = "PASS"

    reasons.extend(
        (
            "INDEPENDENT_SOLVER_VERIFICATION_NOT_PERFORMED",
            "MECHANICAL_QUALIFICATION_NOT_ESTABLISHED",
            "OPTIMIZATION_NOT_ELIGIBLE",
        )
    )
    maximum_stress = max(stress_values) if static_complete else None
    maximum_displacement = max(displacement_values) if static_complete else None
    return {
        "cad_validity_status": cad_status,
        "fea_execution_status": fea_execution_status,
        "recorded_screen_status": recorded_screen_status,
        "buckling_screen_status": buckling_screen_status,
        "mesh_refinement_status": mesh_refinement_status
        if mesh_refinement_status in {"PASS", "FAIL", "UNVERIFIED"}
        else "UNVERIFIED",
        "independent_solver_status": "NOT_PERFORMED",
        "mechanical_qualification_status": "NOT_QUALIFIED",
        "optimization_eligibility": "NOT_QUALIFIED",
        "finest_mesh_level_mm": finest_mesh_level_mm,
        # Kept for legacy readers. It is deliberately never a qualification claim.
        "feasibility_status": "NOT_FEASIBLE_OR_UNVERIFIED",
        "constraints": constraints.to_dict(),
        "maximum_stress_mpa": maximum_stress,
        "maximum_displacement_mm": maximum_displacement,
        "minimum_factor_of_safety": 710.0 / maximum_stress if maximum_stress else None,
        "linear_buckling_factor": buckling_value if buckling_mesh_matches else None,
        "reasons": reasons,
        "feasibility_note": (
            "Legacy feasibility_status is non-passing by design. recorded_screen_status "
            "describes only the recorded numerical screen; independent verification and "
            "mechanical qualification were not performed."
        ),
    }


def objective_mass(mass_kg, assessment):
    """Allow an objective only after explicit qualified/eligible evidence exists."""
    if (
        assessment.get("optimization_eligibility") != "ELIGIBLE"
        or assessment.get("mechanical_qualification_status") != "QUALIFIED"
        or assessment.get("independent_solver_status") != "PASS"
    ):
        raise ValueError(
            "Mass objective is disabled until independently verified mechanical qualification"
        )
    if mass_kg <= 0:
        raise ValueError("Mass must be positive")
    return float(mass_kg)
