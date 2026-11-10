"""Geometry Designer page renderer."""

from pathlib import Path

import pandas as pd
import streamlit as st

from conrod.materials import MATERIALS
from conrod.schemas import BOUNDS, Geometry, MeshSettings
from conrod.visualization import cad_figure


def render_geometry_designer(root, launch):
    st.subheader("Define the authoritative CAD solid")
    st.caption(
        "Dimensions in mm. This legacy single-profile editor preserves the two through-bores; applying it switches away from the Phase 4 parametric family selected in Design Studio."
    )
    with st.form("geometry_form"):
        columns = st.columns(3)
        values = {}
        for i, (key, (lo, hi)) in enumerate(BOUNDS.items()):
            values[key] = columns[i % 3].number_input(
                key.replace("_", " ").title() + " (mm)",
                float(lo),
                float(hi),
                float(st.session_state.geometry[key]),
                step=0.1,
                key="geo_" + key,
            )
        apply = st.form_submit_button("Apply geometry")
        preview = st.form_submit_button("Generate Preview")
    if apply or preview:
        try:
            g = Geometry(**values).validate()
            st.session_state.geometry = g.to_dict()
            st.session_state.phase4_family_design = None
            st.session_state.phase4_cad_output = None
            st.success(
                f"Inputs valid. Web {g.web_thickness:.3f} mm; pocket width {g.pocket_width:.3f} mm."
            )
            if preview:
                launch("CAD_ONLY", MeshSettings(), next(iter(MATERIALS.values())))
        except ValueError as exc:
            st.error(str(exc))
    st.dataframe(
        pd.DataFrame(
            [
                {"Dimension": key.replace("_", " ").title(), "Value (mm)": value}
                for key, value in st.session_state.geometry.items()
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    if st.session_state.get("job_dir"):
        preview = Path(st.session_state.job_dir) / "compression/geometry.stl"
        if preview.exists():
            st.plotly_chart(cad_figure(preview), width="stretch")
