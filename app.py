"""Streamlit entry point for the RodLab Phase 4 research workspace."""

import importlib

import streamlit as st

from conrod.fea import ROOT
from conrod.ui import navigation, theme
from conrod.ui.app_shell import render_job_status
from conrod.ui.state import initialize_session_state

importlib.reload(navigation)
importlib.reload(theme)
theme.configure_page(st)
initialize_session_state(st, ROOT)
st.markdown(
    '<div class="rodlab-brand"><strong>RodLab</strong><span>PHASE 4 · ENGINEERING WORKSPACE</span></div>',
    unsafe_allow_html=True,
)
st.caption(
    "Research prototype · Screening results are not mechanical qualification; independent solver verification has not been performed."
)
render_job_status(streamlit=st)
page = navigation.build_navigation(st)
page.run()
