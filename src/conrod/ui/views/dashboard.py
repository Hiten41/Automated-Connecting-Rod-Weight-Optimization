"""Project dashboard composed from stored Phase 4 engineering evidence."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from conrod.design_exploration import rank_recorded_screen_passes


def render_dashboard(project_root, read, dashboard_diagnostics):
    root = Path(project_root)
    st.subheader("Project overview")
    st.markdown(
        "FreeCAD geometry · Gmsh quadratic mesh · CalculiX structural fields · evidence-led design search"
    )
    evidence_path = root / "data/phase4/phase4-evidence.json"
    study_path = root / "data/phase4/design-space-summary.json"
    dataset_path = root / "data/phase4/dataset-summary.json"
    screen_path = root / "data/phase4/family-screen.json"
    p3_path = root / "data/phase3/feasibility/summary.json"
    convergence_path = root / "evidence/phase3/convergence.json"
    evidence = read(evidence_path) if evidence_path.exists() else None
    study = read(study_path) if study_path.exists() else {}
    dataset = read(dataset_path) if dataset_path.exists() else {}
    p3_study = read(p3_path) if p3_path.exists() else {}
    manifests = (
        root / "runs/phase4-design-space/manifest.json",
        root / "runs/phase4-design-space-lhs/manifest.json",
    )
    manifest_rows = [row for path in manifests if path.is_file() for row in read(path)]
    current_family = st.session_state.get("phase4_family_design")
    current_geometry = (
        str(current_family.get("family", "Parametric family")).replace("_", " ").title()
        if current_family
        else "Filleted v2 · legacy"
    )
    active_loads = st.session_state.get("loads", [])
    load_values = {item["kind"]: item["force_n"] / 1000 for item in active_loads}
    load_summary = (
        f"C {load_values['compression']:.0f} · T {load_values['tension']:.0f} kN"
        if {"compression", "tension"}.issubset(load_values)
        else " / ".join(
            f"{kind[:1].upper()} {force:.0f} kN" for kind, force in load_values.items()
        )
        or "No load cases selected"
    )
    preflight = root / "runs/preflight/preflight.json"
    preflight_ready = preflight.exists() and read(preflight).get("ready")
    overview = st.columns(4)
    overview[0].metric("Current geometry", current_geometry)
    overview[1].metric("Material model", "AISI 4340 · assumed")
    overview[2].metric("Active load model", load_summary)
    overview[3].metric(
        "CAD / FEA solver status", "Ready" if preflight_ready else "Not verified"
    )
    st.caption(
        f"Yield assumption 710 MPa · E = 205 GPa · {st.session_state.load_provenance}. "
        "The COSINE_BEARING model applies equivalent pressure; it is not nonlinear pin contact."
    )
    st.info(
        "Research qualification: results below are recorded refined FEA screening outcomes for a finite tested set. "
        "They do not establish a global optimum, fatigue life, nonlinear contact performance or production certification."
    )

    refined = evidence.get("refined_candidates", []) if evidence else []
    screened_passes = rank_recorded_screen_passes(refined)
    best = screened_passes[0] if screened_passes else None
    reference = next(
        (item for item in refined if item.get("candidate_id") == "P4-0055"), None
    )
    baseline = evidence.get("baseline_phase3", {}) if evidence else {}
    records = int(dataset.get("records", 0))
    attempted = (
        len(manifest_rows) if manifest_rows else int(study.get("total_attempts", 0))
    )
    valid = (
        sum(row.get("status") == "CAD_VALID" for row in manifest_rows)
        if manifest_rows
        else int(study.get("valid_cad_candidates", 0))
    )
    invalid = (
        sum(row.get("status") == "CAD_INVALID" for row in manifest_rows)
        if manifest_rows
        else int(study.get("invalid_or_duplicate_candidates", 0))
    )
    coarse_candidates = len(study.get("coarse_fea_candidate_ids", []))
    rejected_or_unverified = max(0, len(refined) - len(screened_passes))

    st.subheader("Design exploration summary")
    for values in (
        [
            ("Design attempts", attempted),
            ("Valid CAD solids", valid),
            ("Invalid CAD geometries", invalid),
            ("Completed FEA load-case records", records),
        ],
        [
            ("Coarse-screen candidates", coarse_candidates),
            ("Refined candidates", len(refined)),
            ("Passing numerical screens", len(screened_passes)),
            ("Not passing recorded screen", rejected_or_unverified),
        ],
    ):
        cards = st.columns(4)
        for card, (label, value) in zip(cards, values):
            card.metric(label, f"{value:,}")

    selected_level = None
    selected_loads = {}
    selected_checks = None
    if best:
        selected_level = min(best.get("mesh_levels", {}), key=float)
        selected_loads = best["mesh_levels"][selected_level]
        stress_allowable = float(evidence["constraints"]["allowable_stress_mpa"])
        disp_limit = float(evidence["constraints"]["maximum_displacement_mm"])
        tension_stress = selected_loads["tension"]["peak_unaveraged_ip_von_mises_mpa"]
        compression_stress = selected_loads["compression"][
            "peak_unaveraged_ip_von_mises_mpa"
        ]
        max_displacement = max(
            selected_loads["compression"]["max_displacement_mm"],
            selected_loads["tension"]["max_displacement_mm"],
        )
        tension_fos = 710.0 / tension_stress
        buckling_factor = (best.get("buckling") or {}).get("lowest_positive_factor")
        mesh_trend = (
            best["assessment"]
            .get("mesh_refinement", {})
            .get("maximum_peak_stress_change_percent")
        )
        selected_checks = [
            (
                "Compression stress",
                compression_stress,
                stress_allowable,
                "MPa",
                compression_stress <= stress_allowable,
            ),
            (
                "Tension stress",
                tension_stress,
                stress_allowable,
                "MPa",
                tension_stress <= stress_allowable,
            ),
            (
                "Maximum displacement",
                max_displacement,
                disp_limit,
                "mm",
                max_displacement <= disp_limit,
            ),
            (
                "Tension yield factor of safety",
                tension_fos,
                1.8,
                "",
                tension_fos >= 1.8,
            ),
            (
                "Linear buckling factor",
                buckling_factor,
                1.8,
                "",
                buckling_factor is not None and buckling_factor >= 1.8,
            ),
            (
                "Last-pair stress change",
                mesh_trend,
                5.0,
                "%",
                mesh_trend is not None and mesh_trend < 5.0,
            ),
        ]

        st.subheader("Structural performance · lowest-mass recorded-screen pass")
        st.caption(
            f"{best['candidate_id']} · {best['family'].replace('_', ' ').title()} · "
            f"{best['actual_cad_mass_g']:.1f} g · {selected_level} mm finest recorded mesh. "
            "Recorded numerical screen only. Independent solver verification remains NOT_PERFORMED and mechanical qualification remains NOT_QUALIFIED."
        )
        structural = st.columns(4)
        structural[0].metric(
            "Compression peak IP stress",
            f"{compression_stress:.1f} MPa",
            f"FoS {710.0 / compression_stress:.2f} · allowable {stress_allowable:.2f} MPa",
        )
        structural[1].metric(
            "Tension peak IP stress",
            f"{tension_stress:.1f} MPa",
            f"FoS {tension_fos:.2f} · allowable {stress_allowable:.2f} MPa",
        )
        structural[2].metric(
            "Maximum displacement",
            f"{max_displacement:.4f} mm",
            f"limit {disp_limit:.2f} mm",
        )
        structural[3].metric(
            "Linear buckling factor",
            f"{buckling_factor:.2f}" if buckling_factor is not None else "Not run",
            "linear eigenvalue screen",
        )
        checks_frame = pd.DataFrame(
            [
                {
                    "Constraint": label,
                    "Result": f"{value:.3f} {unit}".strip()
                    if value is not None
                    else "Not available",
                    "Limit": f"{limit:.3f} {unit}".strip()
                    if limit is not None
                    else "Not available",
                    "Recorded check": "PASS" if passed else "FAIL",
                }
                for label, value, limit, unit, passed in selected_checks
            ]
        )
        st.dataframe(checks_frame, hide_index=True, width="stretch")
        st.caption(
            "The buckling factor is a linear eigenvalue screen; it does not model nonlinear collapse or postbuckling."
        )
    else:
        st.warning(
            "No refined candidate currently passes the complete recorded numerical screen."
        )

    st.subheader("Optimization and reference comparison")
    if best and reference:
        candidate_mass = float(best["actual_cad_mass_g"])
        reference_mass = float(reference["actual_cad_mass_g"])
        reduction = 100.0 * (reference_mass - candidate_mass) / reference_mass
        cards = st.columns(3)
        cards[0].metric(
            "Phase 3 baseline · fails stress",
            f"{baseline.get('mass_g', 0):.1f} g",
            "unsafe comparison; not a safe reference",
        )
        cards[1].metric("P4-0055 recorded-screen reference", f"{reference_mass:.1f} g")
        cards[2].metric(
            "Lowest-mass recorded-screen candidate",
            f"{candidate_mass:.1f} g",
            f"{reduction:.2f}% below P4-0055",
        )
        st.caption(
            f"The candidate remains {100.0 * (candidate_mass - baseline.get('mass_g', candidate_mass)) / baseline.get('mass_g', candidate_mass):.2f}% heavier than the failing Phase 3 baseline. "
            "P4-0055 and P4-0065 use matched 0.50 mm mesh targets and settings. The finite family search is not a global optimum."
        )

    st.subheader("Engineering visualizations · stored solver data")
    screen_frame = (
        pd.DataFrame(read(screen_path)) if screen_path.exists() else pd.DataFrame()
    )
    if not screen_frame.empty:
        left, right = st.columns(2)
        with left:
            scatter = px.scatter(
                screen_frame,
                x="mass_g",
                y="max_stress_mpa",
                color="family",
                symbol="load",
                hover_data=["candidate_id", "mesh_mm", "status"],
                labels={
                    "mass_g": "Actual CAD mass (g)",
                    "max_stress_mpa": "Peak unaveraged IP stress (MPa)",
                },
                title="Design screening · actual CAD mass vs stress",
            )
            scatter.add_hline(
                y=394.444444,
                line_dash="dash",
                line_color="#b45309",
                annotation_text="394.44 MPa allowable",
            )
            st.plotly_chart(scatter, width="stretch")
        with right:
            paired = (
                screen_frame.pivot_table(
                    index=["candidate_id", "family", "mass_g"],
                    columns="load",
                    values="max_stress_mpa",
                    aggfunc="max",
                )
                .dropna()
                .reset_index()
            )
            if {"compression", "tension"}.issubset(paired.columns):
                paired_fig = px.scatter(
                    paired,
                    x="compression",
                    y="tension",
                    color="family",
                    hover_data=["candidate_id", "mass_g"],
                    labels={
                        "compression": "Compression peak IP stress (MPa)",
                        "tension": "Tension peak IP stress (MPa)",
                    },
                    title="Paired coarse FEA · compression vs tension",
                )
                paired_fig.add_hline(
                    y=394.444444, line_dash="dash", line_color="#b45309"
                )
                paired_fig.add_vline(
                    x=394.444444, line_dash="dash", line_color="#b45309"
                )
                st.plotly_chart(paired_fig, width="stretch")

    if refined:
        displacement_rows = []
        for candidate in refined:
            finest = min(candidate.get("mesh_levels", {}), key=float)
            loads_at_finest = candidate["mesh_levels"][finest]
            displacement_rows.append(
                {
                    "Candidate": candidate["candidate_id"],
                    "Family": candidate["family"],
                    "Finest mesh (mm)": float(finest),
                    "Max displacement (mm)": max(
                        item["max_displacement_mm"] for item in loads_at_finest.values()
                    ),
                }
            )
        left, right = st.columns(2)
        with left:
            displacement_fig = px.bar(
                pd.DataFrame(displacement_rows),
                x="Candidate",
                y="Max displacement (mm)",
                color="Family",
                title="Refined candidate displacement · finest recorded mesh",
            )
            displacement_fig.add_hline(
                y=0.35,
                line_dash="dash",
                line_color="#b45309",
                annotation_text="0.35 mm limit",
            )
            st.plotly_chart(displacement_fig, width="stretch")
        with right:
            mass_rows = pd.DataFrame(
                [
                    {
                        "Candidate": item["candidate_id"],
                        "CAD mass (g)": item["actual_cad_mass_g"],
                        "Recorded screen": item["assessment"]["recorded_screen_status"],
                        "Mesh trend": item["assessment"]["mesh_refinement_status"],
                        "Family": item["family"],
                    }
                    for item in refined
                ]
            ).sort_values("CAD mass (g)")
            mass_fig = px.bar(
                mass_rows,
                x="Candidate",
                y="CAD mass (g)",
                color="Recorded screen",
                hover_data=["Family"],
                title="Refined candidates · actual CAD mass and recorded status",
            )
            st.plotly_chart(mass_fig, width="stretch")

    funnel = pd.DataFrame(
        [
            {"Stage": "CAD attempts", "Candidates": attempted},
            {"Stage": "Valid CAD", "Candidates": valid},
            {"Stage": "Coarse FEA", "Candidates": coarse_candidates},
            {"Stage": "Refined FEA", "Candidates": len(refined)},
            {"Stage": "Pass recorded checks", "Candidates": len(screened_passes)},
        ]
    )
    if attempted:
        st.plotly_chart(
            px.bar(
                funnel,
                x="Stage",
                y="Candidates",
                title="Phase 4 evaluation history · actual processed counts",
                text="Candidates",
            ),
            width="stretch",
        )
    st.caption(
        "No synthetic convergence line is shown: the stored Phase 4 work is a finite design-family search, not an iterative mass-optimization trace."
    )

    if p3_study:
        with st.expander("Phase 3 historical screen", expanded=False):
            history = st.columns(3)
            history[0].metric(
                "CAD geometries sampled", p3_study.get("attempted_geometries", 0)
            )
            history[1].metric(
                "Geometries with actual coarse FEA",
                p3_study.get("actual_fea_geometries", 0),
            )
            history[2].metric(
                "Coarse screen passes", p3_study.get("coarse_screen_passes", 0)
            )
            st.caption(p3_study.get("feasibility_conclusion", "No conclusion recorded"))
            st.caption(
                "The 0.35 mm convergence evidence applies only to the Phase 3 baseline geometry and remains nonnested."
            )
    st.info(
        "Phase 1 historical result: 734.577 g → 384.418 g (47.668%). Sharp pockets, clamped bore, manual loads and mesh-dependent verification; not a safe Phase 4 comparison."
    )
    diagnostic_sources = {}
    for name, path in (
        ("phase3_feasibility", p3_path),
        ("phase3_convergence", convergence_path),
        ("phase4_evidence", evidence_path),
        ("phase4_design_space", study_path),
        ("phase4_dataset_summary", dataset_path),
    ):
        if path.exists():
            diagnostic_sources[name] = read(path)
    dashboard_diagnostics(diagnostic_sources)
