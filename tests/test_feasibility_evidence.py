import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase3_feasibility_summary_does_not_promote_screening_design():
    study = ROOT / "data/phase3/feasibility"
    summary = json.loads((study / "summary.json").read_text(encoding="utf-8"))
    rows = json.loads((study / "candidates.json").read_text(encoding="utf-8"))
    assert summary["attempted_geometries"] == 40
    assert summary["actual_fea_geometries"] == 35
    assert summary["counts"]["INVALID_GEOMETRY_OR_CAD_FAILURE"] == 5
    assert summary["verified_feasible_candidates"] == 0
    assert "INCONCLUSIVE" in summary["feasibility_conclusion"]
    closest = next(row for row in rows if row["index"] == 4)
    assert closest["assessment"]["status"] == "INFEASIBLE_ON_TESTED_MESH"
    refined = summary["refined_near_boundary"][0]
    assert refined["candidate_id"] == 4
    assert refined["status"] == "REFINED_SCREEN_ONLY"
    assert refined["stress_mpa"]["tension"] > 710 / 1.8
