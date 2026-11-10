"""Topology-inspired parametric design-space results view."""

import pandas as pd
import plotly.express as px
import streamlit as st

from conrod.phase4 import Phase4Constraints


def render_topology_explorer(root, read):
    st.subheader("Material distribution and design-space evidence")
    st.info(
        "No SIMP density optimizer is installed or claimed. This workspace uses a "
        "topology-inspired parametric exploration of I, H, tapered, ribbed and rounded-pocket "
        "families; structural labels come from CalculiX."
    )
    study_path = root / "data/phase4/design-space-summary.json"
    family_path = root / "data/phase4/family-screen.json"
    if study_path.exists():
        study = read(study_path)
        st.metric("Valid CAD candidates", study.get("valid_cad_candidates", 0))
        st.write(
            f"{study.get('total_attempts', 0)} distinct attempts · "
            f"{sum(study.get('valid_by_family', {}).values())} valid CAD solids · "
            f"{len(study.get('coarse_fea_candidate_ids', []))} candidates with paired coarse FEA."
        )
        valid_by_family = study.get("valid_by_family", {})
        invalid_by_family = study.get("invalid_by_family", {})
        family_distribution = pd.DataFrame(
            [
                {
                    "Family": family.replace("_", " ").title(),
                    "Valid CAD": valid_by_family.get(family, 0),
                    "Invalid / duplicate": invalid_by_family.get(family, 0),
                }
                for family in sorted(set(valid_by_family) | set(invalid_by_family))
            ]
        )
        if not family_distribution.empty:
            st.markdown("#### CAD validity by family")
            st.dataframe(family_distribution, hide_index=True, width="stretch")
            st.plotly_chart(
                px.bar(
                    family_distribution,
                    x="Family",
                    y=["Valid CAD", "Invalid / duplicate"],
                    barmode="stack",
                    title="Generated geometry outcomes by family",
                ),
                width="stretch",
            )
    evidence_path = root / "data/phase4/phase4-evidence.json"
    if evidence_path.exists():
        evidence = read(evidence_path)
        family_counts = pd.DataFrame(
            [
                {"family": family, "valid CAD designs": count}
                for family, count in evidence["design_space"]["valid_by_family"].items()
            ]
        )
        st.markdown("#### Reproducible design studies")
        st.dataframe(
            pd.DataFrame(evidence["design_space"]["studies"]),
            hide_index=True,
            width="stretch",
        )
        st.bar_chart(family_counts, x="family", y="valid CAD designs")
        final_rows = [
            {
                "Candidate": row["candidate_id"],
                "Family": row["family"],
                "Mass (g)": row["actual_cad_mass_g"],
                "Peak stress (MPa)": row["assessment"]["maximum_stress_mpa"],
                "U max (mm)": row["assessment"]["maximum_displacement_mm"],
                "Last-pair stress change (%)": row["assessment"]
                .get("mesh_refinement", {})
                .get("maximum_peak_stress_change_percent"),
                "Buckling factor": (row["buckling"] or {}).get(
                    "lowest_positive_factor"
                ),
                "Recorded screen": row["assessment"]["recorded_screen_status"],
                "Mesh refinement": row["assessment"]["mesh_refinement_status"],
            }
            for row in evidence["refined_candidates"]
        ]
        st.markdown("#### Refined candidate checks")
        st.dataframe(pd.DataFrame(final_rows), hide_index=True, width="stretch")
    if family_path.exists():
        frame = pd.DataFrame(read(family_path))
        if not frame.empty:
            fig = px.scatter(
                frame,
                x="mass_g",
                y="max_stress_mpa",
                color="family",
                symbol="load",
                hover_data=["candidate_id", "mesh_mm", "status"],
                labels={
                    "mass_g": "Actual CAD mass (g)",
                    "max_stress_mpa": "Peak unaveraged IP stress (MPa)",
                },
                title="Phase 4 family screens · actual CAD mass vs coarse FEA stress",
            )
            fig.add_hline(
                y=Phase4Constraints().allowable_stress_mpa,
                line_dash="dash",
                annotation_text="Historical allowable 394.44 MPa",
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(frame, hide_index=True, width="stretch")
    st.caption(
        "A finite parametric search cannot prove global infeasibility. Candidates are promoted "
        "only after refined FEA, buckling and independent verification."
    )
