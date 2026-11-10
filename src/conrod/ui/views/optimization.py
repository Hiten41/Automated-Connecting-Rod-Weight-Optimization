"""Rank actual Phase 4 candidates without claiming qualification."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_optimization(root, read, rank_recorded_screen_passes, advanced_diagnostics):
    st.subheader("Optimization & feasibility evidence")
    st.caption(
        "This page ranks actual CAD/FEA records from the finite Phase 4 design search. "
        "It does not run a global optimizer or use surrogate predictions as structural constraints."
    )
    evidence_path = root / "data/phase4/phase4-evidence.json"
    evidence = read(evidence_path) if evidence_path.exists() else {}
    candidates = evidence.get("refined_candidates", [])
    screen_passes = rank_recorded_screen_passes(candidates)
    summary_path = root / "data/phase4/design-space-summary.json"
    study = read(summary_path) if summary_path.exists() else {}
    columns = st.columns(4)
    columns[0].metric("Refined candidates", len(candidates))
    columns[1].metric("Recorded numerical screen passes", len(screen_passes))
    columns[2].metric("Independent solver verification", "Not performed")
    columns[3].metric("Mechanical qualification", "Not established")
    st.warning(
        "Mass ranking is exploratory. Independent solver verification, certified material, "
        "validated contact loading, fatigue and production qualification are outstanding."
    )
    if candidates:
        rows = []
        for rank, candidate in enumerate(screen_passes, start=1):
            assessment = candidate["assessment"]
            rows.append(
                {
                    "Screen rank": rank,
                    "Candidate": candidate["candidate_id"],
                    "Family": candidate["family"].replace("_", " ").title(),
                    "CAD mass (g)": candidate["actual_cad_mass_g"],
                    "Peak stress (MPa)": assessment.get("maximum_stress_mpa"),
                    "Yield FoS": assessment.get("minimum_factor_of_safety"),
                    "Mesh target (mm)": assessment.get("finest_mesh_level_mm"),
                    "Mesh trend": assessment.get("mesh_refinement_status"),
                    "Independent verification": assessment.get(
                        "independent_solver_status"
                    ),
                    "Qualification": assessment.get("mechanical_qualification_status"),
                }
            )
        if rows:
            st.markdown("#### Lowest-mass recorded-screen candidates")
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            selected_id = st.selectbox(
                "Inspect candidate evidence",
                [row["candidate_id"] for row in screen_passes],
            )
            selected = next(
                row for row in screen_passes if row["candidate_id"] == selected_id
            )
            detail = st.columns(4)
            detail[0].metric(
                "Candidate CAD mass", f"{selected['actual_cad_mass_g']:.2f} g"
            )
            detail[1].metric(
                "Recorded screen",
                selected["assessment"].get("recorded_screen_status", "UNVERIFIED"),
            )
            detail[2].metric(
                "Finest target",
                f"{selected['assessment'].get('finest_mesh_level_mm', 'N/A')} mm",
            )
            detail[3].metric(
                "Linear buckling factor",
                f"{selected['assessment'].get('linear_buckling_factor'):.3f}"
                if selected["assessment"].get("linear_buckling_factor") is not None
                else "Not available",
            )
            advanced_diagnostics(selected)
        else:
            st.info("No refined candidate passes the full recorded numerical screen.")
        mass_records = []
        for candidate in candidates:
            assessment = candidate.get("assessment", {})
            mass_records.append(
                {
                    "Candidate": candidate["candidate_id"],
                    "CAD mass (g)": candidate["actual_cad_mass_g"],
                    "Peak stress (MPa)": assessment.get("maximum_stress_mpa"),
                    "Recorded screen": assessment.get(
                        "recorded_screen_status", "UNVERIFIED"
                    ),
                }
            )
        chart_data = pd.DataFrame(mass_records).dropna(subset=["Peak stress (MPa)"])
        if not chart_data.empty:
            st.plotly_chart(
                px.scatter(
                    chart_data,
                    x="CAD mass (g)",
                    y="Peak stress (MPa)",
                    color="Recorded screen",
                    hover_name="Candidate",
                    title="Actual refined CAD mass versus recorded peak stress",
                ).add_hline(
                    y=710 / 1.8,
                    line_dash="dash",
                    annotation_text="394.44 MPa recorded allowable",
                ),
                width="stretch",
            )
    exploration = study.get("design_space", {})
    st.markdown("#### Search progress")
    st.caption(
        f"Recorded attempts: {study.get('total_attempts', 'Not available')} · "
        f"valid CAD: {study.get('valid_cad_candidates', 'Not available')} · "
        f"coarse FEA candidate IDs: {len(study.get('coarse_fea_candidate_ids', []))}. "
        "No iterative convergence history or global-optimum proof is present."
    )
    st.caption(
        f"Sampling metadata: {len(exploration.get('studies', []))} recorded studies."
    )
