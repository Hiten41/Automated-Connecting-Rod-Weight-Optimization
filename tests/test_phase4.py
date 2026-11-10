import pytest

from conrod.buckling import parse_buckling_factors
from conrod.design_families import FAMILIES, FamilyDesign
from conrod.design_exploration import (
    lhs_designs,
    mass_stratified_candidates,
    normalized_constraint_margins,
)
from conrod.phase4 import Phase4Constraints, assess_candidate, objective_mass


@pytest.mark.parametrize("family", FAMILIES)
def test_family_defaults_validate_and_are_versioned(family):
    design = FamilyDesign(family=family).validate()
    assert design.geometry_version.startswith("phase4-design-families-v1:")
    assert design.to_dict()["family"] == family
    assert design.length_cc == 145
    assert design.big_end_id == 50
    assert design.small_end_id == 24


@pytest.mark.parametrize(
    "change",
    [
        {"family": "unknown"},
        {"shank_width": 19.0},
        {"beam_thickness": 20.0, "flange_thickness_mm": 8.0},
        {"transition_radius_mm": 4.0, "flange_thickness_mm": 4.0},
    ],
)
def test_invalid_family_designs_rejected(change):
    with pytest.raises(ValueError):
        FamilyDesign(**change).validate()


def _load_results(stress=350.0, displacement=.2):
    return {
        name: {
            "status": "FEA_SUCCESS",
            "max_von_mises_mpa": stress,
            "max_displacement_mm": displacement,
        }
        for name in ("compression", "tension")
    }


def test_coarse_or_unbuckled_results_never_declare_feasibility():
    result = assess_candidate(_load_results(), buckling_factor=3.0)
    assert result["feasibility_status"] == "NOT_FEASIBLE_OR_UNVERIFIED"
    assert "REFINED_INDEPENDENT_VERIFICATION_REQUIRED" in result["reasons"]
    with pytest.raises(ValueError):
        objective_mass(.7, result)


def test_constraint_and_verified_mass_gates():
    result = assess_candidate(
        _load_results(), buckling_factor=2.1, independent_refined=True
    )
    assert result["feasibility_status"] == "FEASIBLE"
    assert result["constraints"]["allowable_stress_mpa"] == pytest.approx(710 / 1.8)
    assert objective_mass(.7, result) == .7


def test_failing_stress_and_buckling_are_reported():
    result = assess_candidate(
        _load_results(stress=500), buckling_factor=1.2, independent_refined=True
    )
    assert result["feasibility_status"] != "FEASIBLE"
    assert "TENSION_STRESS_EXCEEDS_ALLOWABLE" in result["reasons"]
    assert "BUCKLING_FACTOR_BELOW_LIMIT" in result["reasons"]


def test_buckling_factor_parser_requires_real_positive_modes():
    text = "MODE NO       BUCKLING FACTOR\n1 0.7295078E+01\n2 0.2525553E+02\n"
    assert parse_buckling_factors(text) == pytest.approx([7.295078, 25.25553])
    with pytest.raises(ValueError):
        parse_buckling_factors("no eigenvalues in this output")


def test_allowable_stress_stays_on_historical_yield_assumption():
    assert Phase4Constraints().allowable_stress_mpa == pytest.approx(710 / 1.8)


@pytest.mark.parametrize("family", FAMILIES)
def test_latin_hypercube_sampling_is_reproducible_and_valid(family):
    a = lhs_designs(family, count=12, seed=71)
    b = lhs_designs(family, count=12, seed=71)
    assert [x.to_dict() for x in a] == [x.to_dict() for x in b]
    assert all(x.validate() for x in a)


def test_mass_stratified_selection_uses_actual_cad_mass_by_family():
    rows = [
        {"family": family, "status": "CAD_VALID", "actual_cad_mass_g": mass, "id": f"{family}-{mass}"}
        for family in FAMILIES
        for mass in (10, 20, 30, 40)
    ]
    selected = mass_stratified_candidates(rows, per_family=3)
    assert len(selected) == 15
    assert [x["actual_cad_mass_g"] for x in selected[:3]] == [10, 30, 40]


def test_normalized_margins_are_positive_when_constraints_pass():
    margins = normalized_constraint_margins(200, 300, .1, 3.6)
    assert margins["compression_stress"] > 0
    assert margins["tension_stress"] > 0
    assert margins["displacement"] > 0
    assert margins["buckling"] == pytest.approx(1.0)
