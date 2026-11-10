"""Phase 4 engineering workspace. Expensive work only on explicit submission."""

import io
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from conrod.schemas import (
    Geometry,
    LoadCase,
    Constraints,
    MeshSettings,
    BOUNDS,
    Mode,
)
from conrod.materials import MATERIALS
from conrod.fea import ROOT, cad, solve
from conrod.design_families import FAMILIES, FamilyDesign
from conrod.phase4 import Phase4Constraints, assess_candidate
from conrod.engine import Engine, pressure_csv, calculate, plots
from conrod.visualization import (
    cad_figure,
    actual_field_figure,
    solver_field_figure,
    convergence_figure,
)

st.set_page_config(
    page_title="RodLab | Phase 4 engineering workspace", page_icon="⚙", layout="wide"
)
st.markdown(
    """<style>
.block-container{max-width:1380px;padding:1.6rem 1.5rem 3rem}h1{letter-spacing:-.035em;line-height:1.12}
[data-testid="stMetric"]{box-sizing:border-box;min-width:0;height:100%;border:1px solid #53677c38;border-radius:10px;padding:.8rem .95rem;background:linear-gradient(145deg,#fff,#f7fafc)}
[data-testid="stMetricLabel"]{white-space:normal!important;overflow-wrap:anywhere;font-size:.84rem;line-height:1.25}
[data-testid="stMetricValue"]{white-space:normal!important;overflow-wrap:anywhere;word-break:normal;font-size:clamp(1.25rem,1.9vw,2rem);line-height:1.15}
[data-testid="stMetricDelta"]{white-space:normal!important;overflow-wrap:anywhere}
[data-testid="stSidebar"]{border-right:1px solid #53677c38}
.stButton>button{border-radius:8px;min-height:2.5rem}div[data-testid="stCaptionContainer"]{line-height:1.55}
[data-testid="stHorizontalBlock"]{gap:.8rem}
@media(max-width:900px){.block-container{padding:1.2rem 1rem 2.5rem}[data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.65rem}[data-testid="column"]{min-width:min(100%,15rem)!important;flex:1 1 15rem}[data-testid="stMetric"]{padding:.72rem .82rem}}
@media(max-width:560px){.block-container{padding:.85rem .85rem 2rem}h1{font-size:1.75rem!important}[data-testid="stHorizontalBlock"]{gap:.45rem}[data-testid="column"]{min-width:100%!important;max-width:100%!important}[data-testid="stMetricValue"]{font-size:1.45rem}[data-testid="stMetric"]{padding:.65rem .75rem}}
</style>""",
    unsafe_allow_html=True,
)
st.title("RodLab / Phase 4 engineering workspace")
st.caption(
    "GENERATIVE DESIGN · MECHANICS · TRACEABLE EVIDENCE | Bhagavat Pratim Das & Hiten Arora"
)
st.warning(
    "Research prototype. Qualification requires mesh convergence and independent FEA. No fatigue, thermal or nonlinear contact certification."
)
sections = [
    "Dashboard",
    "Geometry Designer",
    "Engine Loading",
    "Simulation",
    "AI Optimization",
    "Results & Comparison",
    "Model Analytics",
    "Reports & Downloads",
    "Phase 4 Design Studio",
    "Topology & Shape Exploration",
]
section = st.sidebar.radio("Workspace", sections)
st.sidebar.caption("Phase 4 · Physics guided geometry and structural evidence")
if "geometry" not in st.session_state:
    st.session_state.geometry = Geometry().to_dict()
if "loads" not in st.session_state:
    st.session_state.loads = [
        LoadCase().to_dict(),
        LoadCase("tension", 18000).to_dict(),
    ]
if "load_provenance" not in st.session_state:
    st.session_state.load_provenance = "MANUAL_REFERENCE_FORCES"
model_path = ROOT / "models/phase3_surrogate.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def advanced_diagnostics(payload):
    """Keep raw engineering structures available only in an opt-in debug panel."""
    with st.expander("Advanced diagnostics — Developer only", expanded=False):
        st.json(payload)


def dashboard_diagnostics(payload):
    """Make dashboard source data downloadable without rendering raw JSON."""
    with st.expander("Advanced diagnostics — Developer only", expanded=False):
        st.caption(
            "Underlying source records are preserved for audit. This export is intended for developers."
        )
        st.download_button(
            "Download dashboard source records",
            json.dumps(payload, indent=2, default=str),
            "rodlab-dashboard-diagnostics.json",
            "application/json",
        )


def launch(action, mesh, material, constraints=Constraints()):
    previous = st.session_state.get("process")
    if previous and previous.poll() is None:
        st.error("A job is still running. Refresh its status before starting another.")
        return
    try:
        mesh.validate()
        constraints.validate()
        g = Geometry(**st.session_state.geometry).validate()
        loads = [LoadCase(**x).validate() for x in st.session_state.loads]
        out = ROOT / "runs/ui-phase3" / uuid.uuid4().hex[:12]
        out.mkdir(parents=True)
        job = dict(
            action=action,
            geometry=g.to_dict(),
            loads=[x.to_dict() for x in loads],
            material=material.to_dict(),
            mesh=mesh.to_dict(),
            constraints=constraints.__dict__,
            output=str(out),
            load_provenance=st.session_state.load_provenance,
        )
        (out / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
        log = open(out / "background.log", "w", encoding="utf-8")
        child_environment = os.environ.copy()
        python_paths = [str(ROOT / "src")]
        if child_environment.get("PYTHONPATH"):
            python_paths.append(child_environment["PYTHONPATH"])
        child_environment["PYTHONPATH"] = os.pathsep.join(python_paths)
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/run_job.py"), str(out / "job.json")],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=child_environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        log.close()
        st.session_state.process = process
        st.session_state.job_dir = str(out)
        st.success(
            f"Job {out.name} started. Frozen inputs saved; use Refresh job status."
        )
    except Exception as exc:
        st.error("Could not start the requested job. Review developer diagnostics for details.")
        advanced_diagnostics({"exception": str(exc)})


def job_status():
    if not st.session_state.get("job_dir"):
        return
    out = Path(st.session_state.job_dir)
    st.sidebar.button("Refresh job status")
    result = out / "ui-result.json"
    if result.exists():
        result = read(result)
        st.sidebar.write("Job status: " + result["status"])
        if result["status"] in ("FAILED", "OPTIMIZATION_FAILED"):
            st.sidebar.error("Analysis failed. Open developer diagnostics for run details.")
    else:
        st.sidebar.info(
            "Job running"
            if st.session_state.process.poll() is None
            else "Job exited without a result; inspect log"
        )
    with st.sidebar.expander("Advanced diagnostics — Developer only", expanded=False):
        log = out / "background.log"
        if log.exists():
            st.sidebar.caption("Raw solver output for the active job.")
            st.code(log.read_text(encoding="utf-8", errors="replace")[-5000:])


job_status()

if section == "Dashboard":
    st.subheader("Project overview")
    st.markdown(
        "FreeCAD geometry · Gmsh quadratic mesh · CalculiX structural fields · evidence-led design search"
    )
    evidence_path = ROOT / "data/phase4/phase4-evidence.json"
    study_path = ROOT / "data/phase4/design-space-summary.json"
    dataset_path = ROOT / "data/phase4/dataset-summary.json"
    screen_path = ROOT / "data/phase4/family-screen.json"
    p3_path = ROOT / "data/phase3/feasibility/summary.json"
    convergence_path = ROOT / "evidence/phase3/convergence.json"
    evidence = read(evidence_path) if evidence_path.exists() else None
    study = read(study_path) if study_path.exists() else {}
    dataset = read(dataset_path) if dataset_path.exists() else {}
    p3_study = read(p3_path) if p3_path.exists() else {}
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
        else " / ".join(f"{kind[:1].upper()} {force:.0f} kN" for kind, force in load_values.items())
        or "No load cases selected"
    )
    preflight = ROOT / "runs/preflight/preflight.json"
    preflight_ready = preflight.exists() and read(preflight).get("ready")
    overview = st.columns(4)
    overview[0].metric("Current geometry", current_geometry)
    overview[1].metric("Material model", "AISI 4340 · assumed")
    overview[2].metric("Active load model", load_summary)
    overview[3].metric(
        "CAD / FEA preflight", "Ready" if preflight_ready else "Not verified"
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
    screened_passes = [
        item for item in refined
        if item.get("assessment", {}).get("feasibility_status") == "FEASIBLE"
    ]
    best = min(screened_passes, key=lambda item: item["actual_cad_mass_g"]) if screened_passes else None
    reference = next((item for item in refined if item.get("candidate_id") == "P4-0055"), None)
    baseline = evidence.get("baseline_phase3", {}) if evidence else {}
    records = int(dataset.get("records", 0))
    attempted = int(study.get("total_attempts", 0))
    valid = int(study.get("valid_cad_candidates", 0))
    invalid = int(study.get("invalid_or_duplicate_candidates", 0))
    coarse_candidates = len(study.get("coarse_fea_candidate_ids", []))
    rejected_or_unverified = max(0, len(refined) - len(screened_passes))

    st.subheader("Design exploration summary")
    for values in (
        [
            ("Design attempts", attempted),
            ("Valid CAD solids", valid),
            ("Invalid / duplicate", invalid),
            ("FEA load-case results", records),
        ],
        [
            ("Coarse-screen candidates", coarse_candidates),
            ("Refined candidates", len(refined)),
            ("Passing recorded screens", len(screened_passes)),
            ("Failed / unverified", rejected_or_unverified),
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
        compression_stress = selected_loads["compression"]["peak_unaveraged_ip_von_mises_mpa"]
        max_displacement = max(
            selected_loads["compression"]["max_displacement_mm"],
            selected_loads["tension"]["max_displacement_mm"],
        )
        tension_fos = 710.0 / tension_stress
        buckling_factor = (best.get("buckling") or {}).get("lowest_positive_factor")
        mesh_trend = best["assessment"].get("mesh_stress_trend_max_percent")
        selected_checks = [
            ("Compression stress", compression_stress, stress_allowable, "MPa", compression_stress <= stress_allowable),
            ("Tension stress", tension_stress, stress_allowable, "MPa", tension_stress <= stress_allowable),
            ("Maximum displacement", max_displacement, disp_limit, "mm", max_displacement <= disp_limit),
            ("Tension yield factor of safety", tension_fos, 1.8, "", tension_fos >= 1.8),
            ("Linear buckling factor", buckling_factor, 1.8, "", buckling_factor is not None and buckling_factor >= 1.8),
            ("Last-pair stress change", mesh_trend, 5.0, "%", mesh_trend is not None and mesh_trend < 5.0),
        ]

        st.subheader("Structural performance · lowest-mass candidate passing recorded checks")
        st.caption(
            f"{best['candidate_id']} · {best['family'].replace('_', ' ').title()} · "
            f"{best['actual_cad_mass_g']:.1f} g · {selected_level} mm finest recorded mesh. "
            "The candidate is a research result, not an independently certified production design."
        )
        structural = st.columns(4)
        structural[0].metric(
            "Compression peak IP stress", f"{compression_stress:.1f} MPa",
            f"FoS {710.0 / compression_stress:.2f} · allowable {stress_allowable:.2f} MPa",
        )
        structural[1].metric(
            "Tension peak IP stress", f"{tension_stress:.1f} MPa",
            f"FoS {tension_fos:.2f} · allowable {stress_allowable:.2f} MPa",
        )
        structural[2].metric(
            "Maximum displacement", f"{max_displacement:.4f} mm",
            f"limit {disp_limit:.2f} mm",
        )
        structural[3].metric(
            "Linear buckling factor",
            f"{buckling_factor:.2f}" if buckling_factor is not None else "Not run",
            "eigenvalue screen · not nonlinear collapse",
        )
        checks_frame = pd.DataFrame(
            [
                {"Constraint": label, "Result": f"{value:.3f} {unit}".strip() if value is not None else "Not available",
                 "Limit": f"{limit:.3f} {unit}".strip() if limit is not None else "Not available",
                 "Recorded check": "PASS" if passed else "FAIL"}
                for label, value, limit, unit, passed in selected_checks
            ]
        )
        st.dataframe(checks_frame, hide_index=True, width="stretch")
    else:
        st.warning("No refined candidate currently passes all recorded Phase 4 checks.")

    st.subheader("Optimization and reference comparison")
    if best and reference:
        candidate_mass = float(best["actual_cad_mass_g"])
        reference_mass = float(reference["actual_cad_mass_g"])
        reduction = 100.0 * (reference_mass - candidate_mass) / reference_mass
        cards = st.columns(3)
        cards[0].metric("Phase 3 baseline · fails stress", f"{baseline.get('mass_g', 0):.1f} g", "unsafe comparison; not a safe reference")
        cards[1].metric("Phase 4 passing reference · P4-0055", f"{reference_mass:.1f} g")
        cards[2].metric("Lowest mass passing recorded checks", f"{candidate_mass:.1f} g", f"{reduction:.2f}% below P4-0055")
        st.caption(
            f"The candidate remains {100.0 * (candidate_mass - baseline.get('mass_g', candidate_mass)) / baseline.get('mass_g', candidate_mass):.2f}% heavier than the failing Phase 3 baseline. "
            "The study is a finite family search; no iterative Phase 4 mass-optimizer convergence trace was recorded."
        )

    st.subheader("Engineering visualizations · stored solver data")
    screen_frame = pd.DataFrame(read(screen_path)) if screen_path.exists() else pd.DataFrame()
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
                labels={"mass_g": "Actual CAD mass (g)", "max_stress_mpa": "Peak unaveraged IP stress (MPa)"},
                title="Design screening · actual CAD mass vs stress",
            )
            scatter.add_hline(y=394.444444, line_dash="dash", line_color="#b45309", annotation_text="394.44 MPa allowable")
            st.plotly_chart(scatter, width="stretch")
        with right:
            paired = screen_frame.pivot_table(
                index=["candidate_id", "family", "mass_g"],
                columns="load", values="max_stress_mpa", aggfunc="max",
            ).dropna().reset_index()
            if {"compression", "tension"}.issubset(paired.columns):
                paired_fig = px.scatter(
                    paired, x="compression", y="tension", color="family",
                    hover_data=["candidate_id", "mass_g"],
                    labels={"compression": "Compression peak IP stress (MPa)", "tension": "Tension peak IP stress (MPa)"},
                    title="Paired coarse FEA · compression vs tension",
                )
                paired_fig.add_hline(y=394.444444, line_dash="dash", line_color="#b45309")
                paired_fig.add_vline(x=394.444444, line_dash="dash", line_color="#b45309")
                st.plotly_chart(paired_fig, width="stretch")

    if refined:
        displacement_rows = []
        for candidate in refined:
            finest = min(candidate.get("mesh_levels", {}), key=float)
            loads_at_finest = candidate["mesh_levels"][finest]
            displacement_rows.append(
                {"Candidate": candidate["candidate_id"], "Family": candidate["family"],
                 "Finest mesh (mm)": float(finest),
                 "Max displacement (mm)": max(item["max_displacement_mm"] for item in loads_at_finest.values())}
            )
        left, right = st.columns(2)
        with left:
            displacement_fig = px.bar(
                pd.DataFrame(displacement_rows), x="Candidate", y="Max displacement (mm)", color="Family",
                title="Refined candidate displacement · finest recorded mesh",
            )
            displacement_fig.add_hline(y=0.35, line_dash="dash", line_color="#b45309", annotation_text="0.35 mm limit")
            st.plotly_chart(displacement_fig, width="stretch")
        with right:
            mass_rows = pd.DataFrame(
                [{"Candidate": item["candidate_id"], "CAD mass (g)": item["actual_cad_mass_g"],
                  "Recorded screen": item["assessment"]["feasibility_status"], "Family": item["family"]}
                 for item in refined]
            ).sort_values("CAD mass (g)")
            mass_fig = px.bar(
                mass_rows, x="Candidate", y="CAD mass (g)", color="Recorded screen",
                hover_data=["Family"], title="Refined candidates · actual CAD mass and recorded status",
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
            px.bar(funnel, x="Stage", y="Candidates", title="Phase 4 evaluation history · actual processed counts", text="Candidates"),
            width="stretch",
        )
    st.caption(
        "No synthetic convergence line is shown: the stored Phase 4 work is a finite design-family search, not an iterative mass-optimization trace."
    )

    if p3_study:
        with st.expander("Phase 3 historical screen", expanded=False):
            history = st.columns(3)
            history[0].metric("CAD geometries sampled", p3_study.get("attempted_geometries", 0))
            history[1].metric("Geometries with actual coarse FEA", p3_study.get("actual_fea_geometries", 0))
            history[2].metric("Coarse screen passes", p3_study.get("coarse_screen_passes", 0))
            st.caption(p3_study.get("feasibility_conclusion", "No conclusion recorded"))
            st.caption("The 0.35 mm convergence evidence applies only to the Phase 3 baseline geometry and remains nonnested.")
    st.info(
        "Phase 1 historical result: 734.577 g → 384.418 g (47.668%). Sharp pockets, clamped bore, manual loads and mesh-dependent verification; not a safe Phase 4 comparison."
    )
    diagnostic_sources = {}
    for name, path in (("phase3_feasibility", p3_path), ("phase3_convergence", convergence_path), ("phase4_evidence", evidence_path), ("phase4_design_space", study_path), ("phase4_dataset_summary", dataset_path)):
        if path.exists():
            diagnostic_sources[name] = read(path)
    dashboard_diagnostics(diagnostic_sources)

elif section == "Geometry Designer":
    st.subheader("Define the authoritative CAD solid")
    st.caption(
        "Dimensions in mm. Fillets preserve through bores; CAD probes verify minimum web and flanges. Radius is fixed during current five-variable optimization."
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
            st.success(
                f"Inputs valid. Web {g.web_thickness:.3f} mm; pocket width {g.pocket_width:.3f} mm."
            )
            if preview:
                launch("CAD_ONLY", MeshSettings(), list(MATERIALS.values())[0])
        except ValueError as exc:
            st.error(str(exc))
    st.dataframe(
        pd.DataFrame(
            [{"Dimension": key.replace("_", " ").title(), "Value (mm)": value}
             for key, value in st.session_state.geometry.items()]
        ),
        hide_index=True,
        width="stretch",
    )
    if st.session_state.get("job_dir"):
        preview = Path(st.session_state.job_dir) / "compression/geometry.stl"
        if preview.exists():
            st.plotly_chart(cad_figure(preview), width="stretch")

elif section == "Engine Loading":
    st.subheader("Loads with explicit provenance")
    mode = st.radio("Loading mode", ["Manual forces", "Engine-derived loading"])
    if mode == "Manual forces":
        with st.form("manual"):
            c = st.number_input("Peak compression (N)", min_value=1.0, value=28000.0)
            t = st.number_input("Peak tension (N)", min_value=1.0, value=18000.0)
            if st.form_submit_button("Use manual loads"):
                st.session_state.loads = [
                    LoadCase("compression", c).to_dict(),
                    LoadCase("tension", t).to_dict(),
                ]
                st.session_state.load_provenance = "MANUAL_USER_FORCES"
                st.success("Manual analysis configuration saved.")
    else:
        source = st.selectbox(
            "Pressure source",
            ["Upload pressure CSV", "Published Hydra plot comparison (approximate)"],
        )
        metadata = read(ROOT / "data/reference_engine/metadata.json")
        if source.startswith("Published"):
            st.warning(
                "Approximate readings from published gas-force plot, not raw cylinder-pressure data. Cross-publication dimensions and neglected dynamics prevent an experimental combustion validation claim."
            )
            st.markdown(
                "[Mufti thesis, Fig 7.2 / 7.4](https://etheses.whiterose.ac.uk/id/eprint/5354/1/414535.pdf) · [Mufti & Priest, Table 1](https://doi.org/10.1115/1.3176988)"
            )
            with st.expander("Source definitions and limitations"):
                st.dataframe(
                    pd.DataFrame(
                        [{"Reference parameter": key.replace("_", " ").title(), "Value": value}
                         for key, value in metadata.get("engine", {}).items()]
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Published gas-force readings are approximate plot extractions, not raw cylinder-pressure data."
                )
                advanced_diagnostics(metadata)
        with st.form("engine"):
            a, b, c = st.columns(3)
            bore = a.number_input("Cylinder bore (mm)", min_value=0.1, value=85.99)
            stroke = b.number_input("Stroke (mm)", min_value=0.1, value=86.0)
            rod = c.number_input("Rod center distance (mm)", min_value=0.1, value=143.5)
            rpm = a.number_input("RPM", min_value=0.0, value=1500.0)
            mass = b.number_input(
                "Effective reciprocating mass (kg)",
                min_value=0.0,
                value=0.5778,
                format="%.4f",
            )
            cycle = c.selectbox("Cycle (degrees)", [720, 360])
            rod_mass = a.number_input(
                "Additional rod mass (kg)", min_value=0.0, value=0.0
            )
            rod_cg = b.number_input(
                "Rod CG fraction from crank pin",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
            )
            st.caption(
                "Optional two-end mass approximation: leave additional rod mass zero if effective reciprocating mass already includes its share. Reference rod mass/CG are not measured inputs here."
            )
            unit = st.selectbox("CSV pressure unit", ["bar", "MPa", "Pa"])
            upload = st.file_uploader(
                "CSV: angle_deg, pressure, optional reference_pressure", type="csv"
            )
            st.caption(
                "0 = firing TDC. Include 0 and cycle endpoint with matching pressure differential. Missing reference_pressure means the supplied pressure is differential. No extrapolation. Effective mass must not include the whole rod by default."
            )
            run = st.form_submit_button("Calculate cycle")
        if run:
            try:
                e = Engine(bore, stroke, rod, rpm, mass, cycle, rod_mass, rod_cg)
                if source.startswith("Published"):
                    if e != Engine(**metadata["engine"]):
                        raise ValueError(
                            "Published comparison requires the exact sourced preset; use CSV mode for other parameters."
                        )
                    observed = pd.read_csv(
                        ROOT / "data/reference_engine/mufti_fig7_2_readings.csv"
                    )
                    p = pd.DataFrame(
                        dict(
                            angle_deg=observed.angle_deg,
                            pressure_pa=observed.gas_force_n
                            / (np.pi * (bore / 1000) ** 2 / 4),
                            reference_pa=0.0,
                        )
                    )
                    provenance = (
                        "APPROXIMATE_PUBLISHED_PLOT_NOT_EXPERIMENTALLY_VALIDATED"
                    )
                else:
                    if upload is None:
                        raise ValueError("Upload a complete pressure CSV.")
                    p = pressure_csv(io.BytesIO(upload.getvalue()), unit, cycle)
                    provenance = "USER_SUPPLIED_PRESSURE_NOT_INDEPENDENTLY_VALIDATED"
                frame, peaks = calculate(e, p)
                st.session_state.engine_result = (frame, peaks, provenance)
            except Exception as exc:
                st.error("Could not calculate the engine cycle from the supplied inputs.")
                advanced_diagnostics({"exception": str(exc)})
        if "engine_result" in st.session_state:
            frame, peaks, provenance = st.session_state.engine_result
            a, b = st.columns(2)
            a.metric(
                "Compression",
                f"{peaks['compression_n']:.1f} N",
                f"at {peaks['compression_angle_deg']:.2f}°",
            )
            b.metric(
                "Tension",
                f"{peaks['tension_n']:.1f} N",
                f"at {peaks['tension_angle_deg']:.2f}°",
            )
            st.caption(provenance)
            if st.button("Use these peak loads in FEA"):
                if min(peaks["compression_n"], peaks["tension_n"]) <= 0:
                    st.error(
                        "This cycle does not have both signed peaks; select a single nonzero case manually."
                    )
                else:
                    st.session_state.loads = [
                        LoadCase("compression", peaks["compression_n"]).to_dict(),
                        LoadCase("tension", peaks["tension_n"]).to_dict(),
                    ]
                    st.session_state.load_provenance = provenance
                    st.session_state.geometry["length_cc"] = peaks["engine"][
                        "rod_length_mm"
                    ]
                    st.success(
                        "Peak loads saved with provenance; CAD center distance synchronized to engine rod length."
                    )
            st.plotly_chart(plots(frame), width="stretch")
            st.download_button(
                "Download cycle CSV",
                frame.to_csv(index=False),
                "engine_cycle.csv",
                "text/csv",
            )

elif section in ("Simulation", "AI Optimization"):
    optimization = section == "AI Optimization"
    model_metadata = read(model_path) if model_path.exists() else {}
    model_eligible = (
        model_metadata.get("model_use") == "ACCEPTED_FOR_OPTIMIZATION"
    )
    st.subheader(
        "Constrained CAD-mass optimization"
        if optimization
        else "Linear elastic simulation"
    )
    st.caption("Active loads: " + st.session_state.load_provenance)
    st.dataframe(
        pd.DataFrame(
            [{"Load case": item["kind"].title(), "Force (N)": item["force_n"]}
             for item in st.session_state.loads]
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
        if optimization:
            fos = a.number_input("Minimum yield FoS", min_value=1.0, value=1.8)
            disp = b.number_input(
                "Maximum displacement (mm)", min_value=0.001, value=0.35
            )
            if not model_path.exists():
                st.warning("Train and evaluate a compatible Phase 3 model first.")
            elif not model_eligible:
                st.warning(
                    model_metadata.get(
                        "optimization_eligibility_note",
                        "The current Phase 3 model is exploratory only; optimizer runs are disabled until held-out evidence supports them.",
                    )
                )
            else:
                st.warning(
                    "The surrogate can screen candidates, not certify them. Any feasible result requires actual FEA and geometry-specific convergence review."
                )
            st.caption(
                "Model: "
                + (
                    read(model_path)["selected_model"]
                    if model_path.exists()
                    else "Phase 3 model unavailable"
                )
            )
        else:
            selection = st.selectbox("Load cases", ["Both", "compression", "tension"])
        submitted = st.form_submit_button(
            "Run Optimization" if optimization else "Run FEA",
            disabled=optimization and not model_eligible,
        )
    if submitted:
        if optimization and not model_path.exists():
            st.error(
                "A compatible Phase 3 model and completed feasibility study are required first."
            )
        else:
            original = st.session_state.loads
            if not optimization and selection != "Both":
                st.session_state.loads = [x for x in original if x["kind"] == selection]
            launch(
                "OPTIMIZE + FEA" if optimization else "FEA",
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
                Constraints(fos, disp) if optimization else Constraints(),
            )
            st.session_state.loads = original

elif section == "Results & Comparison":
    st.subheader("Solver evidence, not surrogate contours")
    paths = sorted((ROOT / "runs").rglob("result.json")) + sorted(
        (ROOT / "data/phase3").rglob("result.json")
    )
    if paths:
        selected = st.selectbox(
            "Analysis record", paths, format_func=lambda p: str(p.relative_to(ROOT))
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
                scale = st.slider("Deformation magnification", 0.0, 100.0, 10.0)
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
                        [{"Region": hotspot.get("region"), "Element": hotspot.get("element_id"),
                          "Integration point": hotspot.get("integration_point"),
                          "X (mm)": xyz[0], "Y (mm)": xyz[1], "Z (mm)": xyz[2]}]
                    ),
                    hide_index=True,
                    width="stretch",
                )
            advanced_diagnostics(
                {k: result.get(k) for k in ["hotspot", "boundary_conditions", "mesh_quality"]}
            )
        else:
            st.error("The selected analysis has no valid structural response. Review developer diagnostics.")
            advanced_diagnostics({"error": result.get("error"), "status": result.get("status")})
        comparisons = st.multiselect(
            "Compare CAD models (choose up to two)",
            paths,
            max_selections=2,
            format_func=lambda p: str(p.relative_to(ROOT)),
        )
        for col, path in zip(st.columns(2), comparisons):
            with col:
                st.caption(str(path.parent.relative_to(ROOT)))
                stl = path.parent / "geometry.stl"
                if stl.exists():
                    st.plotly_chart(cad_figure(stl), width="stretch", key=str(stl))
                geometry_data = read(path).get("geometry", {})
                st.dataframe(
                    pd.DataFrame(
                        [{"Dimension": key.replace("_", " ").title(), "Value": value}
                         for key, value in geometry_data.items()]
                    ),
                    hide_index=True,
                    width="stretch",
                )
    ui_jobs = sorted((ROOT / "runs/ui-phase3").rglob("ui-result.json"))
    if ui_jobs:
        st.subheader("Submitted application jobs")
        selected_job = st.selectbox(
            "Application job",
            ui_jobs,
            format_func=lambda p: str(p.parent.relative_to(ROOT)),
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
                        "CAD solid": "Valid" if cad_result.get("valid_topology") else "Not verified",
                        "Mass (g)": mass_kg * 1000 if mass_kg is not None else None,
                        "Peak stress (MPa)": row.get("max_von_mises_mpa"),
                        "Maximum displacement (mm)": row.get("max_displacement_mm"),
                        "Mesh target (mm)": mesh.get("size_mm"),
                        "Runtime (s)": row.get("runtime_s"),
                    }
                )
            st.dataframe(pd.DataFrame(result_rows), hide_index=True, width="stretch")
        elif job_result.get("verification_attempts"):
            st.caption("Verification attempts are available in the collapsed developer diagnostics panel.")
        elif job_result.get("error"):
            st.error("The submitted analysis did not complete. Open developer diagnostics for details.")
        advanced_diagnostics(job_result)
    experiment = ROOT / "runs/focused-refinement/results.json"
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
    feasibility = ROOT / "data/phase3/feasibility/summary.json"
    if feasibility.exists():
        study = read(feasibility)
        st.subheader("Phase 3 feasibility screening")
        st.metric(
            "Geometries evaluated",
            f"{study['attempted_geometries']} / {study['planned_geometries']}",
        )
        st.write(study["feasibility_conclusion"])
        fcsv = ROOT / "data/phase3/feasibility/feasibility.csv"
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
        (ROOT / "data/phase3/optimization").rglob("optimization.json")
    ) + sorted((ROOT / "runs/ui-phase3").rglob("optimization.json"))
    if optimizations:
        st.subheader("Phase 3 optimization outcome")
        optimization = st.selectbox(
            "Optimization record",
            optimizations,
            format_func=lambda p: str(p.parent.relative_to(ROOT)),
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
        diagnostic = ROOT / "runs/phase3-diagnostic-verification/verification.json"
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
    historical = ROOT / "runs/phase2-optimization/optimization.json"
    if historical.exists():
        with st.expander("Historical Phase 2 failed optimization", expanded=False):
            prior = read(historical)
            st.write(f"Status: {prior['status']}; this is not a Phase 3 result.")
            advanced_diagnostics(prior)

elif section == "Model Analytics":
    st.subheader("Geometry-grouped held-out evaluation")
    analytics_diagnostics = {}
    if model_path.exists():
        md = read(model_path)
        st.markdown(f"**Selected model:** {md['selected_model']}")
        metrics = st.columns(3)
        metrics[0].metric("Labeled samples", md.get("sample_count", "Not recorded"))
        metrics[1].metric("Geometry groups disjoint", "Yes" if md.get("groups_disjoint") else "No / not recorded")
        metrics[2].metric("Near-constraint test rows", md.get("near_constraint_test_count", 0))
        split_counts = md.get("split_counts") or {}
        if split_counts:
            st.markdown("#### Evaluation split")
            st.dataframe(
                pd.DataFrame([{"Split": key.replace("_", " ").title(), "Rows": value}
                              for key, value in split_counts.items()]),
                hide_index=True,
                width="stretch",
            )
        comparisons = pd.json_normalize(md.get("comparisons", []))
        if not comparisons.empty:
            st.markdown("#### Model comparison")
            st.dataframe(comparisons, hide_index=True, width="stretch")
        near_metrics = md.get("near_constraint_metrics")
        if near_metrics:
            st.markdown("#### Near-constraint performance")
            st.dataframe(
                pd.json_normalize(near_metrics, sep=" · ").T.reset_index().rename(
                    columns={"index": "Measure", 0: "Value"}
                ),
                hide_index=True,
                width="stretch",
            )
        predictions = model_path.with_suffix(".test.csv")
        if predictions.exists():
            df = pd.read_csv(predictions)
            for target in ["max_von_mises_mpa", "max_displacement_mm"]:
                a, b = st.columns(2)
                a.plotly_chart(
                    px.scatter(
                        df, x=target + "_actual", y=target + "_predicted", title=target
                    ),
                    width="stretch",
                )
                b.plotly_chart(
                    px.histogram(
                        df, x=target + "_residual", title="FEA minus prediction"
                    ),
                    width="stretch",
                )
        st.caption(
            "Coverage is the training envelope, not a guarantee of accuracy throughout the box."
        )
        st.dataframe(
            pd.DataFrame(
                {
                    "feature": md["features"],
                    "minimum": md["supported_min"],
                    "maximum": md["supported_max"],
                }
            )
        )
        analytics_diagnostics["phase3_model_metadata"] = md
    else:
        st.info(
            "No compatible Phase 3 model trained yet. Historical labels remain separate."
        )
    multifidelity = ROOT / "data/phase2/multifidelity.json"
    if multifidelity.exists():
        multi_data = read(multifidelity)
        st.markdown("#### Historical Phase 2 holdout comparison")
        holdout_metrics = st.columns(3)
        holdout_metrics[0].metric(
            "Held-out fine cases", multi_data.get("held_out_fine_cases", "Not recorded")
        )
        holdout_metrics[1].metric(
            "Held-out geometry groups", len(multi_data.get("held_out_geometry_groups", []))
        )
        holdout_metrics[2].metric(
            "Eligible for optimization",
            "Yes" if multi_data.get("selected_for_optimization") else "No",
        )
        coarse = multi_data.get("coarse_prediction_on_fine", {})
        corrected = multi_data.get("additive_ridge_correction_on_fine", {})
        holdout_rows = [
            {
                "Response": response.replace("_", " ").title(),
                "Statistic": statistic,
                "Coarse model": coarse.get(response, {}).get(statistic),
                "Ridge-corrected model": corrected.get(response, {}).get(statistic),
            }
            for response in ("max_von_mises_mpa", "max_displacement_mm")
            for statistic in ("MAE", "RMSE", "R2")
        ]
        st.dataframe(pd.DataFrame(holdout_rows), hide_index=True, width="stretch")
        st.caption(
            "Two held-out geometry groups only; both model variants remain exploratory and are not used for constraint enforcement."
        )
        analytics_diagnostics["phase2_multifidelity"] = multi_data
    if analytics_diagnostics:
        advanced_diagnostics(analytics_diagnostics)

elif section == "Reports & Downloads":
    st.subheader("Reproduce and inspect")
    docs = (
        sorted((ROOT / "docs/phase4/final").glob("*.md"))
        + sorted((ROOT / "docs/phase4").glob("*.md"))
        + sorted((ROOT / "docs/final").glob("*.md"))
        + sorted((ROOT / "docs").glob("*.md"))
    )
    document = st.selectbox(
        "Engineering report", docs, format_func=lambda p: str(p.relative_to(ROOT))
    )
    st.markdown(document.read_text(encoding="utf-8"))
    st.download_button(
        "Download report", document.read_bytes(), document.name, "text/markdown"
    )
    files = [
        p
        for p in (ROOT / "runs").rglob("*")
        if p.is_file()
        and p.suffix.lower()
        in (".stl", ".step", ".fcstd", ".csv", ".json", ".inp", ".html", ".log", ".png")
    ]
    files.extend(
        p for base in (ROOT / "evidence/phase4", ROOT / "data/phase4")
        if base.exists() for p in base.rglob("*")
        if p.is_file() and p.suffix.lower() in (".zip", ".json", ".jsonl", ".csv", ".png")
    )
    if files:
        artifact = st.selectbox(
            "Analysis artifact",
            sorted(files),
            format_func=lambda p: str(p.relative_to(ROOT)),
        )
        st.download_button(
            "Download selected artifact", artifact.read_bytes(), artifact.name
        )
    st.caption(
        "Input decks, solver logs and field files remain available locally. Use scripts/package_evidence.py for a portable manifest and optional archive."
    )

elif section == "Phase 4 Design Studio":
    st.subheader("Parametric geometry families")
    st.caption(
        "Bore diameters and 145 mm center distance match the historical reference. "
        "Mass is calculated from the generated FreeCAD solid and the historical steel density."
    )
    family_names = {
        "i_section": "I section",
        "h_section": "H section",
        "tapered": "Tapered I section",
        "ribbed": "Locally ribbed I section",
        "pocket_variant": "Rounded pocket H section",
    }
    family = st.selectbox(
        "Geometry family", FAMILIES,
        format_func=lambda value: family_names[value],
        key="phase4_family_select",
    )
    prior = st.session_state.get("phase4_family_design")
    if not prior or prior.get("family") != family:
        prior = FamilyDesign(family=family).to_dict()
    with st.form("phase4_geometry_form"):
        values = dict(prior)
        a, b, c = st.columns(3)
        values["ring_thickness"] = a.number_input(
            "Eye wall (mm)", 6.0, 12.0, float(prior["ring_thickness"]), .2
        )
        values["shank_width"] = b.number_input(
            "Shank width (mm)", 20.0, 44.0, float(prior["shank_width"]), .5
        )
        values["beam_thickness"] = c.number_input(
            "Section depth (mm)", 20.0, 36.0, float(prior["beam_thickness"]), .5
        )
        a, b, c = st.columns(3)
        values["flange_thickness_mm"] = a.number_input(
            "Flange / rail thickness (mm)", 3.0, 10.0,
            float(prior["flange_thickness_mm"]), .25
        )
        values["web_thickness_mm"] = b.number_input(
            "Web thickness (mm)", 3.0, 10.0,
            float(prior["web_thickness_mm"]), .25
        )
        values["transition_radius_mm"] = c.number_input(
            "Eye transition radius (mm)", .5, 4.0,
            float(prior["transition_radius_mm"]), .1
        )
        if family == "tapered":
            a, b, c = st.columns(3)
            for col, name, label in zip(
                (a, b, c),
                ("taper_big_width_mm", "taper_mid_width_mm", "taper_small_width_mm"),
                ("Big end section width (mm)", "Mid shank width (mm)", "Small end section width (mm)"),
            ):
                values[name] = col.number_input(
                    label, 20.0, 44.0, float(prior[name]), .5
                )
        if family == "ribbed":
            a, b = st.columns(2)
            values["rib_height_mm"] = a.number_input(
                "Rib height (mm)", 0.0, 6.0, float(prior["rib_height_mm"]), .25
            )
            values["rib_length_mm"] = b.number_input(
                "Rib run (mm)", 8.0, 35.0, float(prior["rib_length_mm"]), 1.0
            )
        if family == "pocket_variant":
            a, b = st.columns(2)
            values["pocket_length_mm"] = a.number_input(
                "Pocket length (mm)", 10.0, 48.0,
                float(prior["pocket_length_mm"]), 1.0
            )
            values["pocket_width_mm"] = b.number_input(
                "Pocket width (mm)", 6.0, 20.0,
                float(prior["pocket_width_mm"]), .5
            )
        a, b, c = st.columns(3)
        a.metric("Bore center distance", "145 mm")
        b.metric("Big / small bore", "50 / 24 mm")
        c.metric("Historical allowable", "394.44 MPa")
        create_cad = st.form_submit_button("Generate FreeCAD model")
        run_screen = st.form_submit_button("Run paired compression and tension FEA")
    resolution = st.selectbox(
        "Mesh level for paired FEA",
        ["Coarse screen · 6 mm", "Transition refinement · 1.25 mm", "Transition refinement · 0.75 mm", "Fine transition check · 0.5 mm"],
        help="Fine levels take longer. A single mesh, coarse pass or stress-only pass does not certify a design; displacement, buckling and mesh-trend checks also apply.",
    )
    if create_cad or run_screen:
        try:
            design = FamilyDesign(**values).validate()
            st.session_state.phase4_family_design = design.to_dict()
            out = ROOT / "runs/ui-phase4" / uuid.uuid4().hex[:12]
            if create_cad:
                with st.spinner("Generating and checking the FreeCAD solid…"):
                    meta = cad(design, out / "cad")
                st.session_state.phase4_cad_output = str(out / "cad")
                mass_g = meta["volume_mm3"] * MATERIALS["Forged Steel (AISI 4340)"].density_kg_per_mm3 * 1000
                st.success(
                    f"Valid one-solid CAD · {mass_g:.1f} g at the historical steel density · "
                    f"{meta['transition_edges_filleted']} transition edges rounded."
                )
            if run_screen:
                if resolution.startswith("Coarse"):
                    size, hotspot, local = 6.0, None, False
                else:
                    size, hotspot, local = 4.0, float(resolution.split("·")[-1].replace("mm", "").strip()), True
                settings = MeshSettings(
                    size_mm=size, hotspot_size_mm=hotspot, local_refinement=local,
                    refinement_region="big_end_transition",
                )
                out.mkdir(parents=True, exist_ok=True)
                material = MATERIALS["Forged Steel (AISI 4340)"]
                results = {}
                with st.spinner("Running FreeCAD → Gmsh → CalculiX load cases…"):
                    cdir = out / "compression"
                    results["compression"] = solve(
                        design, material, LoadCase("compression", 28000), settings,
                        cdir, Mode.FEA,
                    )
                    tdir = out / "tension"
                    results["tension"] = solve(
                        design, material, LoadCase("tension", 18000), settings,
                        tdir, Mode.FEA,
                        mesh_source=cdir if results["compression"].get("status") == "FEA_SUCCESS" else None,
                    )
                st.session_state.phase4_last_results = results
                st.session_state.phase4_last_dir = str(out)
            st.rerun()
        except Exception as exc:
            st.error("Could not generate or analyze this design. Review developer diagnostics for details.")
            advanced_diagnostics({"exception": str(exc)})
    st.caption(
        "Elastic inputs remain E = 205 GPa, ν = 0.29, density = 7850 kg/m³, "
        "historical yield assumption = 710 MPa. This is not a material certificate."
    )
    cad_dir = st.session_state.get("phase4_cad_output")
    if cad_dir and (Path(cad_dir) / "geometry.stl").exists():
        st.plotly_chart(cad_figure(Path(cad_dir) / "geometry.stl"), width="stretch")
        st.download_button(
            "Download FreeCAD model and parameters",
            (Path(cad_dir) / "geometry.FCStd").read_bytes(),
            "phase4-connecting-rod.FCStd",
            "application/octet-stream",
        )
    results = st.session_state.get("phase4_last_results")
    if results:
        rows = []
        for kind in ("compression", "tension"):
            r = results[kind]
            rows.append({
                "Load": kind.title(), "Status": r.get("status"),
                "Peak unaveraged IP stress (MPa)": r.get("max_von_mises_mpa"),
                "Maximum displacement (mm)": r.get("max_displacement_mm"),
                "Yield FoS on 710 MPa assumption": r.get("factor_of_safety"),
                "Nodes": r.get("node_count"), "Elements": r.get("element_count"),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        constraints = Phase4Constraints()
        checks = [
            results[k].get("status") == "FEA_SUCCESS"
            and results[k].get("max_von_mises_mpa", float("inf")) <= constraints.allowable_stress_mpa
            and results[k].get("max_displacement_mm", float("inf")) <= constraints.maximum_displacement_mm
            for k in ("compression", "tension")
        ]
        if all(checks):
            st.info("Both stress/displacement screens are inside the historical limits. Buckling and independent refinement remain required; this is not a feasibility claim.")
        else:
            st.error("At least one actual FEA stress/displacement screen fails. Mass optimization is disabled until constraints pass.")
        assessment = assess_candidate(results)
        st.markdown(f"**Recorded screen status:** {assessment.get('feasibility_status', 'NOT_ASSESSED')}")
        st.dataframe(
            pd.DataFrame(
                [{"Constraint": key.replace("_", " ").title(), "Value": value}
                 for key, value in assessment.get("constraints", {}).items()]
            ),
            hide_index=True,
            width="stretch",
        )
        advanced_diagnostics(assessment)
        last_dir = st.session_state.get("phase4_last_dir")
        if last_dir:
            for kind in ("compression", "tension"):
                field = Path(last_dir) / kind / "fields.json"
                if field.exists():
                    with st.expander(f"Inspect {kind} solver field"):
                        st.plotly_chart(solver_field_figure(field), width="stretch")

elif section == "Topology & Shape Exploration":
    st.subheader("Material distribution and design-space evidence")
    st.info(
        "No SIMP density optimizer is installed or claimed. This workspace uses a "
        "topology-inspired parametric exploration of I, H, tapered, ribbed and rounded-pocket "
        "families; structural labels come from CalculiX."
    )
    study_path = ROOT / "data/phase4/design-space-summary.json"
    family_path = ROOT / "data/phase4/family-screen.json"
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
            [{"Family": family.replace("_", " ").title(), "Valid CAD": valid_by_family.get(family, 0),
              "Invalid / duplicate": invalid_by_family.get(family, 0)}
             for family in sorted(set(valid_by_family) | set(invalid_by_family))]
        )
        if not family_distribution.empty:
            st.markdown("#### CAD validity by family")
            st.dataframe(family_distribution, hide_index=True, width="stretch")
            st.plotly_chart(
                px.bar(family_distribution, x="Family", y=["Valid CAD", "Invalid / duplicate"],
                       barmode="stack", title="Generated geometry outcomes by family"),
                width="stretch",
            )
    evidence_path = ROOT / "data/phase4/phase4-evidence.json"
    if evidence_path.exists():
        evidence = read(evidence_path)
        family_counts = pd.DataFrame(
            [{"family": family, "valid CAD designs": count}
             for family, count in evidence["design_space"]["valid_by_family"].items()]
        )
        st.markdown("#### Reproducible design studies")
        st.dataframe(pd.DataFrame(evidence["design_space"]["studies"]), hide_index=True, width="stretch")
        st.bar_chart(family_counts, x="family", y="valid CAD designs")
        final_rows = [
            {"Candidate": row["candidate_id"], "Family": row["family"],
             "Mass (g)": row["actual_cad_mass_g"],
             "Peak stress (MPa)": row["assessment"]["maximum_stress_mpa"],
             "U max (mm)": row["assessment"]["maximum_displacement_mm"],
             "Mesh trend (%)": row["assessment"]["mesh_stress_trend_max_percent"],
             "Buckling factor": (row["buckling"] or {}).get("lowest_positive_factor"),
             "Status": row["assessment"]["feasibility_status"]}
            for row in evidence["refined_candidates"]
        ]
        st.markdown("#### Refined candidate checks")
        st.dataframe(pd.DataFrame(final_rows), hide_index=True, width="stretch")
    if family_path.exists():
        frame = pd.DataFrame(read(family_path))
        if not frame.empty:
            fig = px.scatter(
                frame, x="mass_g", y="max_stress_mpa", color="family", symbol="load",
                hover_data=["candidate_id", "mesh_mm", "status"],
                labels={"mass_g": "Actual CAD mass (g)", "max_stress_mpa": "Peak unaveraged IP stress (MPa)"},
                title="Phase 4 family screens · actual CAD mass vs coarse FEA stress",
            )
            fig.add_hline(
                y=Phase4Constraints().allowable_stress_mpa, line_dash="dash",
                annotation_text="Historical allowable 394.44 MPa",
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(frame, hide_index=True, width="stretch")
    st.caption(
        "A finite parametric search cannot prove global infeasibility. Candidates are promoted "
        "only after refined FEA, buckling and independent verification."
    )
