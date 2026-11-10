"""Page dispatch and shared UI dependencies for the Streamlit entry point."""

from functools import partial

import streamlit as st

from conrod.design_exploration import rank_recorded_screen_passes
from conrod.fea import ROOT
from conrod.ui.app_shell import (
    launch_job,
    read_json,
    render_advanced_diagnostics,
    render_dashboard_diagnostics,
)
from conrod.ui.data_access import load_phase4_ml_evaluation, phase4_prediction_records
from conrod.ui.views.dashboard import render_dashboard
from conrod.ui.views.design_studio import render_design_studio
from conrod.ui.views.engine_loading import render_engine_loading
from conrod.ui.views.geometry_designer import render_geometry_designer
from conrod.ui.views.model_analytics import render_model_analytics
from conrod.ui.views.optimization import render_optimization
from conrod.ui.views.reports import render_reports
from conrod.ui.views.results import render_results
from conrod.ui.views.simulation import render_simulation
from conrod.ui.views.topology_explorer import render_topology_explorer


def render_named_page(page_name):
    """Render one page using the existing engineering modules and shared data."""
    advanced = partial(render_advanced_diagnostics, streamlit=st)
    dashboard_diagnostics = partial(render_dashboard_diagnostics, streamlit=st)
    launch = partial(launch_job, project_root=ROOT, streamlit=st)
    renderers = {
        "dashboard": lambda: render_dashboard(ROOT, read_json, dashboard_diagnostics),
        "legacy_geometry_editor": lambda: render_geometry_designer(ROOT, launch),
        "engine_loading": lambda: render_engine_loading(ROOT, read_json, advanced),
        "simulation": lambda: render_simulation(ROOT, launch),
        "optimization_feasibility": lambda: render_optimization(
            ROOT, read_json, rank_recorded_screen_passes, advanced
        ),
        "results_comparison": lambda: render_results(ROOT, read_json, advanced),
        "model_analytics": lambda: render_model_analytics(
            ROOT,
            read_json,
            load_phase4_ml_evaluation,
            phase4_prediction_records,
            advanced,
        ),
        "reports_downloads": lambda: render_reports(ROOT),
        "design_studio": lambda: render_design_studio(ROOT, advanced),
        "design_space_explorer": lambda: render_topology_explorer(ROOT, read_json),
    }
    if page_name not in renderers:
        raise ValueError(f"Unknown Phase 4 page: {page_name}")
    renderers[page_name]()
