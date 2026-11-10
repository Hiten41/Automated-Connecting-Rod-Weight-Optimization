"""Session defaults and recovery of persisted Phase 4 application jobs."""

from conrod.schemas import Geometry, LoadCase


def initialize_session_state(st, project_root):
    if "geometry" not in st.session_state:
        st.session_state.geometry = Geometry().to_dict()
    if "loads" not in st.session_state:
        st.session_state.loads = [
            LoadCase().to_dict(),
            LoadCase("tension", 18000).to_dict(),
        ]
    if "load_provenance" not in st.session_state:
        st.session_state.load_provenance = "MANUAL_REFERENCE_FORCES"
    if not st.session_state.get("job_dir"):
        saved_jobs = sorted(
            (project_root / "runs/ui-phase4").glob("*/job.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if saved_jobs:
            st.session_state.job_dir = str(saved_jobs[0].parent)
            st.session_state.process = None
