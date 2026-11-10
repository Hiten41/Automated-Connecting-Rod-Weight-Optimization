"""Narrow, typed accessors for data shown by the Streamlit UI."""

import json
import os
from pathlib import Path


def phase4_ml_evaluation_path(project_root):
    """Return the canonical Phase 4 model evaluation path."""
    return Path(project_root) / "data" / "phase4" / "ml-evaluation.json"


def load_phase4_ml_evaluation(project_root):
    """Load Phase 4 evaluation data without historical-model fallback."""
    path = phase4_ml_evaluation_path(project_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def phase4_prediction_records(evaluation, split=None):
    """Return persisted genuine Phase 4 predictions, optionally for one split."""
    records = evaluation.get("row_level_predictions", [])
    required = {
        "evaluation",
        "model",
        "candidate_id",
        "geometry_hash",
        "load_case",
        "mesh_fidelity",
        "actual_stress_mpa",
        "predicted_stress_mpa",
        "residual_mpa",
        "fold_id",
    }
    filtered = [
        row for row in records if split is None or row.get("evaluation") == split
    ]
    for row in filtered:
        missing = required - row.keys()
        if missing:
            raise ValueError(
                f"Phase 4 prediction record is missing fields: {sorted(missing)}"
            )
        if row.get("evaluation") not in {
            "coarse_grouped_5fold_oof",
            "coarse_trained_fine_geometry_holdout",
        }:
            raise ValueError("Unknown Phase 4 prediction split")
    return filtered


def job_status_snapshot(job_dir, process=None, pid_is_running=None):
    """Recover a persisted UI job state after a Streamlit rerun or reconnect."""
    folder = Path(job_dir)
    result_path = folder / "ui-result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        return {"state": "FINISHED", "result": result}
    if process is not None and process.poll() is None:
        return {"state": "RUNNING", "result": None}
    metadata_path = folder / "process.json"
    if metadata_path.is_file():
        try:
            pid = int(json.loads(metadata_path.read_text(encoding="utf-8"))["pid"])
            checker = pid_is_running or _pid_is_running
            if checker(pid):
                return {"state": "RUNNING", "result": None}
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            pass
    return {"state": "EXITED_WITHOUT_RESULT", "result": None}


def _pid_is_running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
