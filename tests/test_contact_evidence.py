import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contact_evidence_keeps_flat_and_curved_scope_distinct():
    evidence = json.loads(
        (ROOT / "evidence/phase3/contact-validation.json").read_text(
            encoding="utf-8"
        )
    )
    assert all(
        row["audit"]["status"] == "PATCH_TEST_PASSED"
        for row in evidence["patch_tests"]
    )
    assert evidence["pin_status"] == "NOT VALIDATED FOR ROD INTEGRATION"
    assert len(evidence["pin_tests"]) == 4
    assert all(row["active_contact_samples"] > 0 for row in evidence["pin_tests"])
    assert evidence["checks"]["reaction_equilibrium_passed"]
    assert not evidence["checks"]["pressure_sensitivity_passed"]
    assert evidence["checks"]["peak_pressure_relative_change_32_to_96"] > 0.05
    assert evidence["checks"][
        "peak_pressure_relative_change_penalty_1e6_to_1e7_at_96"
    ] > 0.05
