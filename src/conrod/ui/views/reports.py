"""Reports & Downloads page renderer."""

import json

import pandas as pd
import streamlit as st


def render_reports(root):
    st.subheader("Reports and reproducible project data")
    st.caption(
        "Engineering reports and curated exports use stored Phase 4 results. Raw solver fields and input decks are available on Results & Comparison."
    )
    docs = sorted(set((root / "docs/phase4/final").glob("*.md")))
    if not docs:
        st.info("No Phase 4 final reports are available in this checkout.")
        return
    document = st.selectbox(
        "Engineering report",
        docs,
        format_func=lambda p: p.stem.replace("_", " ").replace("-", " ").title(),
    )
    st.markdown(document.read_text(encoding="utf-8"))
    st.download_button(
        "Download report", document.read_bytes(), document.name, "text/markdown"
    )
    evidence_path = root / "data/phase4/phase4-evidence.json"
    if evidence_path.is_file():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        export_rows = []
        for row in evidence.get("refined_candidates", []):
            assessment = row.get("assessment", {})
            level = assessment.get("finest_mesh_level_mm")
            level_data = row.get("mesh_levels", {}).get(str(level), {})
            export_rows.append(
                {
                    "Candidate": row.get("candidate_id"),
                    "Family": row.get("family"),
                    "CAD mass (g)": row.get("actual_cad_mass_g"),
                    "Assessment mesh (mm)": level,
                    "Compression stress (MPa)": (
                        level_data.get("compression") or {}
                    ).get("peak_unaveraged_ip_von_mises_mpa"),
                    "Tension stress (MPa)": (level_data.get("tension") or {}).get(
                        "peak_unaveraged_ip_von_mises_mpa"
                    ),
                    "Maximum displacement (mm)": assessment.get(
                        "maximum_displacement_mm"
                    ),
                    "Minimum yield FoS": assessment.get("minimum_factor_of_safety"),
                    "Linear buckling factor": assessment.get("linear_buckling_factor"),
                    "Recorded screen": assessment.get("recorded_screen_status"),
                    "Mesh refinement": assessment.get("mesh_refinement_status"),
                    "Independent solver verification": assessment.get(
                        "independent_solver_status"
                    ),
                    "Mechanical qualification": assessment.get(
                        "mechanical_qualification_status"
                    ),
                }
            )
        if export_rows:
            st.markdown("#### Candidate summary export")
            st.download_button(
                "Download refined candidate summary CSV",
                pd.DataFrame(export_rows).to_csv(index=False),
                "phase4-refined-candidate-summary.csv",
                "text/csv",
            )

    prediction_path = root / "data/phase4/ml-evaluation.json"
    if prediction_path.is_file():
        predictions = json.loads(prediction_path.read_text(encoding="utf-8")).get(
            "row_level_predictions", []
        )
        if predictions:
            st.download_button(
                "Download genuine Phase 4 ML prediction records CSV",
                pd.DataFrame(predictions).to_csv(index=False),
                "phase4-row-level-ml-predictions.csv",
                "text/csv",
            )

    st.markdown("#### Review packages")
    packages = [
        root / "outputs/RodLab-Phase4-Core-Deliverables-under512MB.zip",
        root
        / "outputs/phase4-complete-review-bundle/rodLab-phase4-complete-source.zip",
    ]
    available_packages = [path for path in packages if path.is_file()]
    if available_packages:
        package_rows = [
            {
                "Package": path.name,
                "Size (MB)": round(path.stat().st_size / 1_000_000, 2),
                "Available": "Yes",
            }
            for path in available_packages
        ]
        st.dataframe(pd.DataFrame(package_rows), hide_index=True, width="stretch")
        package = st.selectbox(
            "Project review package", available_packages, format_func=lambda p: p.name
        )
        st.download_button(
            "Download project review package",
            package.read_bytes(),
            package.name,
            "application/zip",
        )
    else:
        st.info(
            "A packaged project review ZIP has not been built in this checkout yet."
        )

    artifact_roots = (root / "runs/phase4-refined", root / "runs/ui-phase4")
    allowed_extensions = {
        ".stl",
        ".step",
        ".fcstd",
        ".csv",
        ".inp",
        ".frd",
        ".dat",
        ".sta",
        ".msh",
        ".png",
        ".html",
    }
    artifacts = [
        path
        for base in artifact_roots
        if base.is_dir()
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in allowed_extensions
    ]
    artifacts = sorted(artifacts, key=lambda path: path.stat().st_mtime, reverse=True)[
        :500
    ]
    if artifacts:
        st.markdown("#### CAD and solver artifact library")
        artifact = st.selectbox(
            "Stored engineering artifact",
            artifacts,
            format_func=lambda path: str(path.relative_to(root)),
        )
        st.download_button(
            "Download stored engineering artifact",
            artifact.read_bytes(),
            artifact.name,
        )
    st.caption(
        "Exports retain source-record values. CSV summaries do not replace the raw solver fields, mesh files, or independent mechanical review."
    )
