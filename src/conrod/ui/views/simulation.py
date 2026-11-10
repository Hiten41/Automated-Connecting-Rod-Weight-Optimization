"""Linear elastic CAD/FEA simulation submission page."""

import pandas as pd
import streamlit as st

from conrod.materials import MATERIALS
from conrod.schemas import Constraints, MeshSettings


def render_simulation(root, launch):
    st.subheader("Linear elastic simulation")
    st.caption("Active loads: " + st.session_state.load_provenance)
    st.dataframe(
        pd.DataFrame(
            [
                {"Load case": item["kind"].title(), "Force (N)": item["force_n"]}
                for item in st.session_state.loads
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    with st.form("simulation"):
        material = st.selectbox("Material", list(MATERIALS))
        a, b = st.columns(2)
        size = a.selectbox(
            "Maximum mesh size (mm)", [4.0, 2.5, 1.75, 1.25, 1.0, 0.75, 5.0, 6.0]
        )
        bc = b.selectbox(
            "Boundary conditions", ["COSINE_BEARING", "LEGACY_CLAMPED_BORE"]
        )
        local = st.checkbox(
            "Local refinement around transitions and pockets", value=True
        )
        strategy = st.selectbox(
            "Local mesh strategy",
            [
                "Full-thickness big-end transition",
                "Focused junctions and pocket corners",
                "All CAD curves",
            ],
        )
        local_size = st.number_input(
            "Focused target size (mm)",
            min_value=0.25,
            max_value=float(size),
            value=min(0.75, float(size)),
            step=0.25,
        )
        st.caption(
            "Quadratic tetrahedra · linear static · two solver threads · 600 s solver timeout · 250,000-node solve budget"
        )
        selection = st.selectbox("Load cases", ["Both", "compression", "tension"])
        submitted = st.form_submit_button("Run FEA")
    if submitted:
        original = st.session_state.loads
        if selection != "Both":
            st.session_state.loads = [x for x in original if x["kind"] == selection]
        launch(
            "FEA",
            MeshSettings(
                size,
                boundary_mode=bc,
                local_refinement=local,
                hotspot_size_mm=local_size
                if local and not strategy.startswith("All")
                else None,
                refinement_region="big_end_transition"
                if strategy.startswith("Full")
                else "all_features",
            ),
            MATERIALS[material],
            Constraints(),
        )
        st.session_state.loads = original
