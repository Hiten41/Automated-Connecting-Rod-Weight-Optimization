"""Shared application data access, diagnostics and background job controls."""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from conrod.design_families import FamilyDesign
from conrod.fea import ROOT
from conrod.schemas import Constraints, Geometry, LoadCase
from conrod.ui.data_access import job_status_snapshot


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def render_advanced_diagnostics(payload, *, streamlit=st):
    """Keep raw engineering structures inside the collapsed developer panel."""
    with streamlit.expander("Advanced diagnostics — Developer only", expanded=False):
        streamlit.json(payload)


def render_dashboard_diagnostics(payload, *, streamlit=st):
    with streamlit.expander("Advanced diagnostics — Developer only", expanded=False):
        streamlit.caption(
            "Underlying source records are preserved for audit. This export is intended for developers."
        )
        streamlit.download_button(
            "Download dashboard source records",
            json.dumps(payload, indent=2, default=str),
            "rodlab-dashboard-diagnostics.json",
            "application/json",
        )


def launch_job(
    action,
    mesh,
    material,
    constraints=None,
    *,
    project_root=ROOT,
    streamlit=st,
    advanced_diagnostics=render_advanced_diagnostics,
):
    if constraints is None:
        constraints = Constraints()
    previous = streamlit.session_state.get("process")
    if previous and previous.poll() is None:
        streamlit.error(
            "A job is still running. Refresh its status before starting another."
        )
        return
    try:
        mesh.validate()
        constraints.validate()
        family_design = streamlit.session_state.get("phase4_family_design")
        geometry = (
            FamilyDesign(**family_design).validate()
            if family_design
            else Geometry(**streamlit.session_state.geometry).validate()
        )
        loads = [LoadCase(**case).validate() for case in streamlit.session_state.loads]
        output_dir = project_root / "runs/ui-phase4" / uuid.uuid4().hex[:12]
        output_dir.mkdir(parents=True)
        job = {
            "action": action,
            "geometry": geometry.to_dict(),
            "loads": [case.to_dict() for case in loads],
            "material": material.to_dict(),
            "mesh": mesh.to_dict(),
            "constraints": constraints.__dict__,
            "output": str(output_dir),
            "load_provenance": streamlit.session_state.load_provenance,
        }
        job_path = output_dir / "job.json"
        job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
        child_environment = os.environ.copy()
        python_paths = [str(project_root / "src")]
        if child_environment.get("PYTHONPATH"):
            python_paths.append(child_environment["PYTHONPATH"])
        child_environment["PYTHONPATH"] = os.pathsep.join(python_paths)
        with (output_dir / "background.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(project_root / "scripts/run_job.py"),
                    str(job_path),
                ],
                cwd=project_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=child_environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        (output_dir / "process.json").write_text(
            json.dumps(
                {
                    "pid": process.pid,
                    "started_at": datetime.now().astimezone().isoformat(),
                }
            ),
            encoding="utf-8",
        )
        streamlit.session_state.process = process
        streamlit.session_state.job_dir = str(output_dir)
        streamlit.success(
            f"Job {output_dir.name} started. Frozen inputs saved; use Refresh job status."
        )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        streamlit.error(
            "Could not start the requested job. Review developer diagnostics for details."
        )
        advanced_diagnostics({"exception": str(exc)})


def render_job_status(project_root=ROOT, *, streamlit=st):
    if not streamlit.session_state.get("job_dir"):
        return
    output_dir = Path(streamlit.session_state.job_dir)
    streamlit.sidebar.button("Refresh job status", key="refresh_job_status")
    snapshot = job_status_snapshot(
        output_dir,
        process=streamlit.session_state.get("process"),
    )
    if snapshot["state"] == "FINISHED":
        result = snapshot["result"]
        streamlit.sidebar.write("Job status: " + result["status"])
        if result["status"] in ("FAILED", "OPTIMIZATION_FAILED"):
            streamlit.sidebar.error(
                "Analysis failed. Open developer diagnostics for run details."
            )
    else:
        streamlit.sidebar.info(
            "Job running"
            if snapshot["state"] == "RUNNING"
            else "Job exited without a result; inspect developer diagnostics"
        )
    with streamlit.sidebar.expander(
        "Advanced diagnostics — Developer only", expanded=False
    ):
        log_path = output_dir / "background.log"
        if log_path.exists():
            streamlit.caption("Raw solver output for the active job.")
            streamlit.code(
                log_path.read_text(encoding="utf-8", errors="replace")[-5000:]
            )
