import pytest

from conrod.buckling import parse_buckling_factors
from conrod.design_exploration import (
    lhs_designs,
    mass_stratified_candidates,
    normalized_constraint_margins,
)
from conrod.design_families import FAMILIES, FamilyDesign
from conrod.phase4 import (
    Phase4Constraints,
    assess_candidate,
    finest_successful_mesh_level,
    mesh_refinement_summary,
    objective_mass,
    ordered_mesh_levels,
    static_pair_passes,
)


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


def test_rounded_pocket_uses_positive_effective_width_at_clearance_boundary():
    design = FamilyDesign(
        family="pocket_variant",
        shank_width=30.0,
        flange_thickness_mm=10.0,
        pocket_width_mm=12.0,
        pocket_length_mm=10.0,
    ).validate()
    assert design.effective_pocket_width_mm == pytest.approx(8.0)


@pytest.mark.parametrize(
    "change",
    [
        {"shank_width": 20.0, "flange_thickness_mm": 10.0},
        {
            "shank_width": 44.0,
            "flange_thickness_mm": 3.0,
            "pocket_width_mm": 20.0,
            "pocket_length_mm": 19.0,
        },
    ],
)
def test_rounded_pocket_rejects_nonpositive_clearance_or_short_capsule(change):
    with pytest.raises(ValueError, match="Rounded pocket"):
        FamilyDesign(family="pocket_variant", **change).validate()


def _load_results(stress=350.0, displacement=0.2):
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
    assert result["recorded_screen_status"] == "UNVERIFIED"
    assert result["independent_solver_status"] == "NOT_PERFORMED"
    assert result["mechanical_qualification_status"] == "NOT_QUALIFIED"
    assert result["optimization_eligibility"] == "NOT_QUALIFIED"
    with pytest.raises(ValueError):
        objective_mass(0.7, result)


def test_numerical_screen_pass_does_not_promote_independent_or_qualified_status():
    result = assess_candidate(
        _load_results(),
        buckling_factor=2.1,
        cad_validity_status="CAD_VALID",
        mesh_refinement_status="PASS",
        buckling_mesh_matches=True,
    )
    assert result["recorded_screen_status"] == "PASS"
    assert result["mesh_refinement_status"] == "PASS"
    assert result["independent_solver_status"] == "NOT_PERFORMED"
    assert result["mechanical_qualification_status"] == "NOT_QUALIFIED"
    assert result["optimization_eligibility"] == "NOT_QUALIFIED"
    assert result["feasibility_status"] == "NOT_FEASIBLE_OR_UNVERIFIED"
    assert result["constraints"]["allowable_stress_mpa"] == pytest.approx(710 / 1.8)
    with pytest.raises(ValueError):
        objective_mass(0.7, result)


def test_failing_stress_and_buckling_are_reported():
    result = assess_candidate(
        _load_results(stress=500),
        buckling_factor=1.2,
        cad_validity_status="CAD_VALID",
        buckling_mesh_matches=True,
    )
    assert result["feasibility_status"] != "FEASIBLE"
    assert result["recorded_screen_status"] == "FAIL"
    assert "TENSION_STRESS_EXCEEDS_ALLOWABLE" in result["reasons"]
    assert "BUCKLING_FACTOR_BELOW_LIMIT" in result["reasons"]


def test_missing_load_case_or_mesh_association_never_silently_passes():
    partial = {"compression": _load_results()["compression"]}
    result = assess_candidate(
        partial,
        buckling_factor=3.0,
        cad_validity_status="CAD_VALID",
        buckling_mesh_matches=False,
    )
    assert result["fea_execution_status"] == "FAIL"
    assert result["recorded_screen_status"] == "UNVERIFIED"
    assert result["buckling_screen_status"] == "UNVERIFIED"
    assert result["maximum_stress_mpa"] is None
    assert "BOTH_LOAD_CASES_REQUIRED" in result["reasons"]
    assert "BUCKLING_MESH_ASSOCIATION_MISMATCH" in result["reasons"]


@pytest.mark.parametrize("invalid", [None, float("nan"), float("inf"), -1.0])
def test_refinement_static_screen_never_passes_missing_or_invalid_fields(invalid):
    cases = _load_results()
    cases["tension"]["max_von_mises_mpa"] = invalid
    assert static_pair_passes(cases, 710 / 1.8, 0.35) is False


def test_refinement_static_screen_requires_both_cases_and_constraints():
    cases = _load_results(stress=350.0, displacement=0.2)
    assert static_pair_passes(cases, 710 / 1.8, 0.35) is True
    cases["tension"]["max_displacement_mm"] = 0.36
    assert static_pair_passes(cases, 710 / 1.8, 0.35) is False
    del cases["compression"]
    assert static_pair_passes(cases, 710 / 1.8, 0.35) is False


def test_mesh_targets_are_numerically_sorted_and_finest_successful_selected():
    def pair(status="FEA_SUCCESS", stress=200):
        return {
            name: {
                "status": status,
                "max_von_mises_mpa": stress,
                "max_displacement_mm": 0.1,
            }
            for name in ("compression", "tension")
        }

    results = {
        "0.75": pair(stress=210),
        "1.25": pair(stress=200),
        "0.5": pair(status="FAILED"),
    }
    assert ordered_mesh_levels(results) == ("1.25", "0.75", "0.5")
    assert finest_successful_mesh_level(results) == "0.75"
    assert finest_successful_mesh_level({"0.5": pair(status="FAILED")}) is None
    with pytest.raises(ValueError, match="Duplicate numeric"):
        ordered_mesh_levels(("0.50", "0.5"))


def test_mesh_trend_uses_only_last_adjacent_pair():
    def pair(compression, tension):
        return {
            "compression": {
                "status": "FEA_SUCCESS",
                "max_von_mises_mpa": compression,
                "max_displacement_mm": 0.05,
            },
            "tension": {
                "status": "FEA_SUCCESS",
                "max_von_mises_mpa": tension,
                "max_displacement_mm": 0.09,
            },
        }

    results = {"1.25": pair(100, 100), "0.75": pair(200, 200), "0.5": pair(205, 210)}
    summary = mesh_refinement_summary(results)
    assert summary["pair_levels_mm"] == [0.75, 0.5]
    assert summary["maximum_peak_stress_change_percent"] == pytest.approx(5.0)
    assert summary["status"] == "FAIL"
    assert summary["interpretation"] == "CONTINUUM_MESH_ERROR_NOT_ESTABLISHED"


def test_p4_0065_consolidated_assessment_uses_finest_mesh_and_matching_buckling():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    data = json.loads(
        (root / "data/phase4/phase4-evidence.json").read_text(encoding="utf-8")
    )
    candidate = next(
        row for row in data["refined_candidates"] if row["candidate_id"] == "P4-0065"
    )
    assessment = candidate["assessment"]
    assert assessment["finest_mesh_level_mm"] == pytest.approx(0.5)
    assert assessment["maximum_stress_mpa"] == pytest.approx(366.005861, abs=1e-5)
    assert assessment["minimum_factor_of_safety"] == pytest.approx(1.93986, abs=1e-4)
    assert assessment["linear_buckling_factor"] == pytest.approx(7.196246)
    assert candidate["buckling"]["mesh_level_mm"] == pytest.approx(0.5)
    assert candidate["buckling"]["mesh_association_status"] == "PASS"
    assert assessment["independent_solver_status"] == "NOT_PERFORMED"
    assert assessment["mechanical_qualification_status"] == "NOT_QUALIFIED"
    assert assessment["maximum_stress_mpa"] != pytest.approx(349.110538, abs=1e-5)


def test_p4_0055_and_p4_0065_have_matched_half_mm_mesh_settings():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    data = json.loads(
        (root / "data/phase4/phase4-evidence.json").read_text(encoding="utf-8")
    )
    comparison = data["matched_fidelity_candidate_comparison"]
    assert comparison["local_target_mm"] == pytest.approx(0.5)
    assert comparison["mesh_settings_equal"] is True
    assert comparison["distinct_candidate_geometries_meshed_separately"] is True
    assert comparison["mass_difference_percent_p4_0065_vs_p4_0055"] == pytest.approx(
        -3.8345, abs=0.001
    )
    candidates = {row["candidate_id"]: row for row in data["refined_candidates"]}
    p4_0055 = candidates["P4-0055"]
    p4_0065 = candidates["P4-0065"]
    assert p4_0055["assessment"]["finest_mesh_level_mm"] == pytest.approx(0.5)
    assert p4_0055["assessment"]["maximum_stress_mpa"] == pytest.approx(
        280.546206, abs=1e-5
    )
    assert p4_0055["buckling"]["mesh_level_mm"] == pytest.approx(0.5)
    assert (
        p4_0055["mesh_levels"]["0.5"]["compression"]["mesh_settings"]
        == comparison["mesh_settings"]
    )
    assert (
        p4_0065["mesh_levels"]["0.5"]["compression"]["mesh_settings"]
        == comparison["mesh_settings"]
    )


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
        {
            "family": family,
            "status": "CAD_VALID",
            "actual_cad_mass_g": mass,
            "id": f"{family}-{mass}",
        }
        for family in FAMILIES
        for mass in (10, 20, 30, 40)
    ]
    selected = mass_stratified_candidates(rows, per_family=3)
    assert len(selected) == 15
    assert [x["actual_cad_mass_g"] for x in selected[:3]] == [10, 30, 40]


def test_normalized_margins_are_positive_when_constraints_pass():
    margins = normalized_constraint_margins(200, 300, 0.1, 3.6)
    assert margins["compression_stress"] > 0
    assert margins["tension_stress"] > 0
    assert margins["displacement"] > 0
    assert margins["buckling"] == pytest.approx(1.0)
