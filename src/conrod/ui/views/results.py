"""Curated view of refined Phase 4 candidates and their raw solver fields."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from conrod.schemas import Geometry, LoadCase
from conrod.visualization import (
    actual_field_figure,
    cad_figure,
    convergence_figure,
    solver_field_figure,
)


def _project_path(project_root, value):
    path = Path(value)
    return path if path.is_absolute() else Path(project_root) / path


def render_refined_candidate_results(project_root, read_json):
    """Render the final candidate assessment with its matching mesh and fields."""
    root = Path(project_root)
    evidence_path = root / "data/phase4/phase4-evidence.json"
    st.subheader("Refined candidate results")
    st.caption(
        "The selected structural fields, mesh statistics and buckling record are read from the same stored mesh level."
    )
    if not evidence_path.is_file():
        st.info("Consolidated Phase 4 candidate evidence is not available.")
        return
    candidates = read_json(evidence_path).get("refined_candidates", [])
    if not candidates:
        st.info("No refined candidates are recorded.")
        return
    candidate = st.selectbox(
        "Refined candidate",
        candidates,
        format_func=lambda row: (
            f"{row['candidate_id']} · {row['actual_cad_mass_g']:.1f} g · "
            f"{row['assessment'].get('recorded_screen_status', 'UNVERIFIED')} recorded screen"
        ),
        key="results_candidate_id",
    )
    levels = candidate.get("mesh_levels", {})
    if not levels:
        st.warning("The candidate has no recorded mesh-level results.")
        return
    level_options = sorted(levels, key=float)
    default_level = str(candidate.get("assessment_mesh_level_mm", level_options[0]))
    if default_level not in levels:
        default_level = min(level_options, key=float)
    a, b = st.columns(2)
    mesh_level = a.selectbox(
        "Mesh target (mm)",
        level_options,
        index=level_options.index(default_level),
        format_func=lambda value: f"{float(value):g} mm",
        key="results_mesh_level",
    )
    load_case = b.selectbox(
        "Load case",
        ["compression", "tension"],
        format_func=str.title,
        key="results_load_case",
    )
    case = levels[mesh_level].get(load_case, {})
    if case.get("status") != "FEA_SUCCESS":
        st.error("The selected load case has no successful solver result.")
        return

    metrics = st.columns(4)
    metrics[0].metric("Actual CAD mass", f"{candidate['actual_cad_mass_g']:.2f} g")
    metrics[1].metric(
        "Peak unaveraged IP stress",
        f"{case['peak_unaveraged_ip_von_mises_mpa']:.3f} MPa",
    )
    metrics[2].metric("Maximum displacement", f"{case['max_displacement_mm']:.5f} mm")
    metrics[3].metric(
        "Yield FoS on 710 MPa assumption",
        f"{case['factor_of_safety_710_mpa']:.3f}",
    )
    quality = case.get("mesh_quality") or {}
    boundary = case.get("boundary_conditions") or {}
    result_rows = [
        {"Recorded quantity": "Mesh nodes", "Value": str(case.get("nodes"))},
        {"Recorded quantity": "C3D10 elements", "Value": str(case.get("elements"))},
        {
            "Recorded quantity": "Global minSICN",
            "Value": str(quality.get("minSICN_min")),
        },
        {
            "Recorded quantity": "minSICN 1st percentile",
            "Value": str(quality.get("minSICN_p01")),
        },
        {"Recorded quantity": "FEA runtime (s)", "Value": str(case.get("runtime_s"))},
        {"Recorded quantity": "Boundary model", "Value": boundary.get("model")},
        {
            "Recorded quantity": "Force balance fraction",
            "Value": str(
                (boundary.get("equilibrium") or {}).get("force_balance_fraction")
            ),
        },
    ]
    st.dataframe(pd.DataFrame(result_rows), hide_index=True, width="stretch")
    st.caption(
        "COSINE_BEARING is an equivalent prescribed frictionless radial-pressure approximation. "
        "It is not nonlinear pin contact. The reported global element-quality minimum is retained; "
        "the stress is the actual unaveraged integration-point maximum."
    )
    assessment = candidate.get("assessment", {})
    buckling = candidate.get("buckling") or {}
    status_columns = st.columns(4)
    status_columns[0].metric(
        "Recorded screen", assessment.get("recorded_screen_status", "UNVERIFIED")
    )
    status_columns[1].metric(
        "Last-pair mesh trend", assessment.get("mesh_refinement_status", "UNVERIFIED")
    )
    status_columns[2].metric(
        "Independent solver verification",
        assessment.get("independent_solver_status", "NOT_PERFORMED"),
    )
    status_columns[3].metric(
        "Mechanical qualification",
        assessment.get("mechanical_qualification_status", "NOT_QUALIFIED"),
    )
    if buckling.get("mesh_level_mm") is not None:
        st.caption(
            f"Same-mesh linear eigenvalue buckling factor: {buckling.get('lowest_positive_factor', 'N/A')} "
            f"at {buckling['mesh_level_mm']:g} mm; not nonlinear collapse or ultimate capacity."
        )

    fields_path = case.get("fields_path")
    output_dir = case.get("output_dir")
    fields_file = _project_path(root, fields_path) if fields_path else None
    output_folder = _project_path(root, output_dir) if output_dir else None
    if fields_file and fields_file.is_file():
        display = st.selectbox(
            "Solver field display",
            [
                "Unaveraged integration-point stress",
                "Deformed nodal displacement",
                "Element mean point cloud",
            ],
        )
        scale = st.slider(
            "Deformation magnification",
            0.0,
            100.0,
            10.0,
            key=f"refined_deformation_scale_{candidate['candidate_id']}_{load_case}_{mesh_level}",
        )
        figure = (
            solver_field_figure(fields_file)
            if display.startswith("Element")
            else actual_field_figure(
                fields_file,
                "displacement" if display.startswith("Deformed") else "stress",
                scale,
            )
        )
        st.plotly_chart(figure, width="stretch")
        st.caption(
            "Stress points use actual quadratic-element Gauss coordinates. Display may be decimated; "
            "the peak marker and displayed maximum come from the full stored field. Displacement uses "
            "actual nodal vectors with the selected magnification."
        )
        st.download_button(
            "Download field visualization",
            figure.to_html(include_plotlyjs=True),
            f"{candidate['candidate_id']}-{load_case}-field.html",
            "text/html",
        )
        field_data = json.loads(fields_file.read_text(encoding="utf-8"))
        st.download_button(
            "Download raw solver field JSON",
            json.dumps(field_data, separators=(",", ":")),
            f"{candidate['candidate_id']}-{load_case}-fields.json",
            "application/json",
        )
    else:
        st.warning(
            "The raw field file referenced by this summary is missing from this checkout."
        )

    if output_folder and output_folder.is_dir():
        cad_file = output_folder / "geometry.stl"
        if cad_file.is_file():
            st.markdown("#### Matching CAD geometry")
            st.plotly_chart(cad_figure(cad_file), width="stretch")
        downloads = [
            output_folder / "result.json",
            output_folder / "job.inp",
            output_folder / "mesh.msh",
            output_folder / "job.frd",
            output_folder / "job.dat",
        ]
        available = [path for path in downloads if path.is_file()]
        if available:
            artifact = st.selectbox(
                "Raw solver artifact",
                available,
                format_func=lambda path: path.name,
            )
            st.download_button(
                "Download raw solver artifact",
                artifact.read_bytes(),
                f"{candidate['candidate_id']}-{load_case}-{artifact.name}",
            )
    with st.expander("Advanced diagnostics — Developer only", expanded=False):
        st.json(
            {
                "hotspot": case.get("hotspot"),
                "boundary_conditions": boundary,
                "mesh_quality": quality,
            }
        )


def render_results(root, read, advanced_diagnostics):
    render_refined_candidate_results(root, read)
    st.markdown("---")
    st.subheader("Other stored solver results")
    paths = sorted((root / "runs").rglob("result.json")) + sorted(
        (root / "data/phase3").rglob("result.json")
    )
    if paths:
        selected = st.selectbox(
            "Analysis record", paths, format_func=lambda p: str(p.relative_to(root))
        )
        result = read(selected)
        st.write("Status: " + result["status"])
        if result.get("status") == "FEA_SUCCESS":
            cols = st.columns(4)
            for col, label, key in zip(
                cols,
                ["CAD mass (g)", "Peak IP stress (MPa)", "Maximum U (mm)", "Yield FoS"],
                [
                    "mass_kg",
                    "max_von_mises_mpa",
                    "max_displacement_mm",
                    "factor_of_safety",
                ],
            ):
                col.metric(
                    label, f"{result[key] * (1000 if key == 'mass_kg' else 1):.4f}"
                )
            if "family" in result.get("geometry", {}):
                buckling_path = selected.parent.parent / "buckling/buckling.json"
                if buckling_path.exists():
                    buckling_result = read(buckling_path)
                    st.metric(
                        "Linear buckling factor",
                        f"{buckling_result['lowest_positive_factor']:.3f}",
                    )
                    st.caption(
                        "CalculiX linear eigenvalue result. It does not include imperfections or nonlinear postbuckling."
                    )
                else:
                    st.caption(
                        "Analytical Euler screening is not applied to this parametric family geometry. No eigenvalue result is recorded for this mesh."
                    )
            else:
                from conrod.analytical import evaluate
                from conrod.schemas import Material

                screening = evaluate(
                    Geometry(**result["geometry"]),
                    Material(**result["material"]),
                    LoadCase(**result["load"]),
                )
                st.caption(
                    "Analytical Euler buckling screening margin: "
                    + str(screening.get("buckling_margin"))
                    + ". Not nonlinear buckling validation."
                )
            st.warning(result.get("convergence_status", "Convergence not demonstrated"))
            st.caption(
                f"Load case: {result['load'].get('kind', 'unknown')} · "
                f"{result['load'].get('force_n', 0):,.0f} N · "
                f"mesh target {result['mesh'].get('size_mm', 'unknown')} mm · "
                f"boundary model {result['mesh'].get('boundary_mode', 'unknown')}"
            )
            fields = selected.parent / "fields.json"
            if fields.exists():
                display = st.selectbox(
                    "Field display",
                    [
                        "Unaveraged integration-point stress",
                        "Deformed nodal displacement",
                        "Element mean point cloud",
                    ],
                )
                scale = st.slider(
                    "Deformation magnification",
                    0.0,
                    100.0,
                    10.0,
                    key=f"recorded_deformation_scale_{selected.parent.name}",
                )
                figure = (
                    solver_field_figure(fields)
                    if display.startswith("Element")
                    else actual_field_figure(
                        fields,
                        "displacement" if display.startswith("Deformed") else "stress",
                        scale,
                    )
                )
                st.plotly_chart(figure, width="stretch")
                st.download_button(
                    "Download current field plot",
                    figure.to_html(include_plotlyjs=True),
                    "actual_solver_field.html",
                    "text/html",
                )
                st.caption(
                    "Stress points use actual quadratic-element Gauss coordinates. No surface stress extrapolation. Display may be decimated; the peak marker uses all results. Displacement uses actual nodal vectors, with the stated magnification."
                )
            hotspot = result.get("hotspot") or {}
            if hotspot:
                st.markdown("#### Peak stress location")
                xyz = hotspot.get("coordinates_mm") or [None, None, None]
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Region": hotspot.get("region"),
                                "Element": hotspot.get("element_id"),
                                "Integration point": hotspot.get("integration_point"),
                                "X (mm)": xyz[0],
                                "Y (mm)": xyz[1],
                                "Z (mm)": xyz[2],
                            }
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
            advanced_diagnostics(
                {
                    k: result.get(k)
                    for k in ["hotspot", "boundary_conditions", "mesh_quality"]
                }
            )
        else:
            st.error(
                "The selected analysis has no valid structural response. Review developer diagnostics."
            )
            advanced_diagnostics(
                {"error": result.get("error"), "status": result.get("status")}
            )
        comparisons = st.multiselect(
            "Compare CAD models (choose up to two)",
            paths,
            max_selections=2,
            format_func=lambda p: str(p.relative_to(root)),
        )
        for col, path in zip(st.columns(2), comparisons):
            with col:
                st.caption(str(path.parent.relative_to(root)))
                stl = path.parent / "geometry.stl"
                if stl.exists():
                    st.plotly_chart(cad_figure(stl), width="stretch", key=str(stl))
                geometry_data = read(path).get("geometry", {})
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Dimension": key.replace("_", " ").title(),
                                "Value": str(value),
                            }
                            for key, value in geometry_data.items()
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
    ui_jobs = sorted(
        list((root / "runs/ui-phase4").rglob("ui-result.json"))
        + list((root / "runs/ui-phase3").rglob("ui-result.json"))
    )
    if ui_jobs:
        st.subheader("Submitted application jobs")
        selected_job = st.selectbox(
            "Application job",
            ui_jobs,
            format_func=lambda p: str(p.parent.relative_to(root)),
        )
        job_result = read(selected_job)
        st.write("Status: " + job_result.get("status", "UNKNOWN"))
        st.caption("Load provenance: " + job_result.get("load_provenance", "unknown"))
        if job_result.get("results"):
            result_rows = []
            for row in job_result["results"]:
                load = row.get("load", {})
                mesh = row.get("mesh", {})
                cad_result = row.get("cad", {})
                mass_kg = row.get("mass_kg")
                result_rows.append(
                    {
                        "Load case": load.get("kind", "Unknown").title(),
                        "Status": row.get("status", "UNKNOWN"),
                        "CAD solid": "Valid"
                        if cad_result.get("valid_topology")
                        else "Not verified",
                        "Mass (g)": mass_kg * 1000 if mass_kg is not None else None,
                        "Peak stress (MPa)": row.get("max_von_mises_mpa"),
                        "Maximum displacement (mm)": row.get("max_displacement_mm"),
                        "Mesh target (mm)": mesh.get("size_mm"),
                        "Runtime (s)": row.get("runtime_s"),
                    }
                )
            st.dataframe(pd.DataFrame(result_rows), hide_index=True, width="stretch")
        elif job_result.get("verification_attempts"):
            st.caption(
                "Verification attempts are available in the collapsed developer diagnostics panel."
            )
        elif job_result.get("error"):
            st.error(
                "The submitted analysis did not complete. Open developer diagnostics for details."
            )
        advanced_diagnostics(job_result)
    experiment = root / "runs/focused-refinement/results.json"
    if experiment.exists():
        rows = [
            r
            for r in read(experiment)
            if r["mesh"]["boundary_mode"] == "COSINE_BEARING"
        ]
        st.subheader("Mesh convergence")
        st.plotly_chart(convergence_figure(rows), width="stretch")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        k: r.get(k)
                        for k in [
                            "status",
                            "node_count",
                            "element_count",
                            "max_von_mises_mpa",
                            "max_displacement_mm",
                            "runtime_s",
                        ]
                    }
                    | {
                        "mesh_mm": r["mesh"]["size_mm"],
                        "local_target_mm": r["mesh"].get("hotspot_size_mm"),
                        "load": r["load"]["kind"],
                    }
                    for r in rows
                ]
            )
        )
    feasibility = root / "data/phase3/feasibility/summary.json"
    if feasibility.exists():
        study = read(feasibility)
        st.subheader("Phase 3 feasibility screening")
        st.metric(
            "Geometries evaluated",
            f"{study['attempted_geometries']} / {study['planned_geometries']}",
        )
        st.write(study["feasibility_conclusion"])
        fcsv = root / "data/phase3/feasibility/feasibility.csv"
        if fcsv.exists():
            frame = pd.read_csv(fcsv)
            st.dataframe(frame)
            if "tension_stress_mpa" in frame:
                st.plotly_chart(
                    px.scatter(
                        frame,
                        x="mass_g",
                        y="tension_stress_mpa",
                        color="status",
                        hover_data=["index"],
                        title="Actual 6mm FEA screening; coarse results require refinement",
                    ),
                    width="stretch",
                )
    optimizations = sorted(
        (root / "data/phase3/optimization").rglob("optimization.json")
    ) + sorted((root / "runs/ui-phase3").rglob("optimization.json"))
    if optimizations:
        st.subheader("Phase 3 optimization outcome")
        optimization = st.selectbox(
            "Optimization record",
            optimizations,
            format_func=lambda p: str(p.parent.relative_to(root)),
        )
        outcome = read(optimization)
        st.write("Status: " + outcome["status"])
        if outcome.get("optimized_mass_kg") is not None:
            a, b, c = st.columns(3)
            a.metric(
                "Starting CAD mass (g)", f"{outcome['baseline_mass_kg'] * 1000:.3f}"
            )
            b.metric(
                "Candidate CAD mass (g)", f"{outcome['optimized_mass_kg'] * 1000:.3f}"
            )
            c.metric("Mass reduction (%)", f"{outcome['mass_reduction_pct']:.3f}")
            st.warning(
                "Independent FEA constraint pass only; mechanical qualification still requires geometry-specific convergence."
            )
        else:
            st.warning(
                "No independently verified feasible optimum is available. No mass reduction is claimed."
            )
        diagnostics = outcome.get("diagnostics", [])
        if diagnostics:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Attempt": index,
                            "Converged": "Yes" if diagnostic.get("success") else "No",
                            "Iterations": diagnostic.get("iterations"),
                            "Final mass / baseline": diagnostic.get("objective"),
                        }
                        for index, diagnostic in enumerate(diagnostics, start=1)
                    ]
                )
            )
            st.plotly_chart(
                px.line(
                    x=list(range(1, len(diagnostics) + 1)),
                    y=[d["objective"] for d in diagnostics],
                    markers=True,
                    labels={
                        "x": "Multistart attempt",
                        "y": "Final mass / baseline mass",
                    },
                ),
                width="stretch",
            )
        advanced_diagnostics(outcome)
        diagnostic = root / "runs/phase3-diagnostic-verification/verification.json"
        if diagnostic.exists():
            checks = read(diagnostic)
            st.subheader("Independent checks of rejected search points")
            st.caption(
                "Diagnostic designs only. These are not accepted optima; tension strength checks failed."
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "candidate": i + 1,
                            "load": r["load"]["kind"],
                            "mass_g": r.get("mass_kg", 0) * 1000,
                            "stress_MPa": r.get("max_von_mises_mpa"),
                            "displacement_mm": r.get("max_displacement_mm"),
                            "yield_FoS": r.get("factor_of_safety"),
                            "status": r["status"],
                        }
                        for i, c in enumerate(checks["candidates"])
                        for r in c["fea"]
                    ]
                )
            )
    historical = root / "runs/phase2-optimization/optimization.json"
    if historical.exists():
        with st.expander("Historical Phase 2 failed optimization", expanded=False):
            prior = read(historical)
            st.write(f"Status: {prior['status']}; this is not a Phase 3 result.")
            advanced_diagnostics(prior)
