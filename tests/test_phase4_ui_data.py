import json
from pathlib import Path

import pytest

from conrod.design_exploration import rank_recorded_screen_passes
from conrod.ui.data_access import (
    job_status_snapshot,
    load_phase4_ml_evaluation,
    phase4_ml_evaluation_path,
    phase4_prediction_records,
)


def test_phase4_ml_loader_uses_only_the_phase4_evaluation_path(tmp_path):
    p4_path = phase4_ml_evaluation_path(tmp_path)
    p4_path.parent.mkdir(parents=True)
    p4_path.write_text(json.dumps({"source": "phase4"}), encoding="utf-8")
    historical = tmp_path / "models" / "phase3_surrogate.json"
    historical.parent.mkdir()
    historical.write_text(json.dumps({"source": "phase3"}), encoding="utf-8")

    assert load_phase4_ml_evaluation(tmp_path) == {"source": "phase4"}
    assert load_phase4_ml_evaluation(tmp_path)["source"] != "phase3"


def test_missing_phase4_ml_data_does_not_fall_back_to_phase3(tmp_path):
    historical = tmp_path / "models" / "phase3_surrogate.json"
    historical.parent.mkdir()
    historical.write_text(json.dumps({"source": "phase3"}), encoding="utf-8")
    assert load_phase4_ml_evaluation(tmp_path) is None


def test_persisted_phase4_predictions_and_geometry_group_splits_are_genuine():
    root = Path(__file__).resolve().parents[1]
    evaluation = load_phase4_ml_evaluation(root)
    dataset = evaluation["dataset"]
    assert dataset["rows"] == 86
    assert dataset["grouping_key"] == "geometry_hash"
    assert dataset["coarse_geometry_groups_disjoint"] is True
    assert dataset["fine_holdout_disjoint_from_coarse_training"] is True
    assert set(dataset["fine_holdout_geometry_hashes"]).isdisjoint(
        dataset["fine_training_geometry_hashes"]
    )
    for fold in evaluation["coarse_grouped_fold_audit"]:
        assert fold["geometry_hashes_disjoint"] is True
        assert set(fold["train_geometry_hashes"]).isdisjoint(
            fold["test_geometry_hashes"]
        )
    predictions = phase4_prediction_records(evaluation)
    assert len(predictions) == 216
    assert {row["model"] for row in predictions} == {"Ridge", "Extra Trees", "MLP"}
    assert {row["evaluation"] for row in predictions} == {
        "coarse_grouped_5fold_oof",
        "coarse_trained_fine_geometry_holdout",
    }
    assert all(row["geometry_hash"] and row["candidate_id"] for row in predictions)
    assert all(
        row["residual_mpa"]
        == pytest.approx(row["actual_stress_mpa"] - row["predicted_stress_mpa"])
        for row in predictions
    )


def test_phase4_predictions_reject_historical_phase3_labels():
    with pytest.raises(ValueError, match="Unknown Phase 4 prediction split"):
        phase4_prediction_records(
            {
                "row_level_predictions": [
                    {
                        "evaluation": "phase3_test",
                        "model": "MLP",
                        "candidate_id": "old",
                        "geometry_hash": "hash",
                        "load_case": "tension",
                        "mesh_fidelity": "historical",
                        "actual_stress_mpa": 1,
                        "predicted_stress_mpa": 1,
                        "residual_mpa": 0,
                        "fold_id": None,
                    }
                ]
            }
        )


def test_candidate_ranking_requires_explicit_phase4_screen_status():
    rows = [
        {
            "candidate_id": "qualified-is-not-implied",
            "actual_cad_mass_g": 10,
            "assessment": {"feasibility_status": "FEASIBLE"},
        },
        {
            "candidate_id": "recorded-pass",
            "actual_cad_mass_g": 20,
            "assessment": {"recorded_screen_status": "PASS"},
        },
        {
            "candidate_id": "recorded-fail",
            "actual_cad_mass_g": 1,
            "assessment": {"recorded_screen_status": "FAIL"},
        },
    ]
    assert [row["candidate_id"] for row in rank_recorded_screen_passes(rows)] == [
        "recorded-pass"
    ]


def test_job_status_recovers_running_finished_and_abandoned_runs(tmp_path):
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "process.json").write_text(json.dumps({"pid": 42}), encoding="utf-8")
    assert (
        job_status_snapshot(job_dir, pid_is_running=lambda pid: pid == 42)["state"]
        == "RUNNING"
    )
    assert (
        job_status_snapshot(job_dir, pid_is_running=lambda _pid: False)["state"]
        == "EXITED_WITHOUT_RESULT"
    )

    class RunningProcess:
        @staticmethod
        def poll():
            return None

    assert job_status_snapshot(job_dir, process=RunningProcess())["state"] == "RUNNING"
    (job_dir / "ui-result.json").write_text(
        json.dumps({"status": "COMPLETED"}), encoding="utf-8"
    )
    snapshot = job_status_snapshot(job_dir, process=RunningProcess())
    assert snapshot == {"state": "FINISHED", "result": {"status": "COMPLETED"}}
