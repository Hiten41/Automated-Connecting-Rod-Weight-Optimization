"""Phase 2 engineering workspace. Expensive work only on explicit submission."""

import io
import json
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
    GEOMETRY_VERSION,
)
from conrod.materials import MATERIALS
from conrod.fea import ROOT, configuration
from conrod.engine import Engine, pressure_csv, calculate, plots
from conrod.visualization import (
    cad_figure,
    actual_field_figure,
    solver_field_figure,
    convergence_figure,
)

st.set_page_config(
    page_title="RodLab | Engineering workspace", page_icon="⚙", layout="wide"
)
st.markdown(
    """<style>
.block-container{max-width:1500px;padding-top:2rem}h1{letter-spacing:-.04em}
[data-testid="stMetric"]{border:1px solid #53677c44;border-radius:12px;padding:16px}
[data-testid="stSidebar"]{border-right:1px solid #53677c44}
.stButton>button{border-radius:8px}div[data-testid="stCaptionContainer"]{line-height:1.6}
</style>""",
    unsafe_allow_html=True,
)
st.title("RodLab / Engineering workspace")
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
]
section = st.sidebar.radio("Workspace", sections)
st.sidebar.caption("Phase 2 · Filleted geometry · Cosine bearing pressure")
if "geometry" not in st.session_state:
    st.session_state.geometry = Geometry().to_dict()
if "loads" not in st.session_state:
    st.session_state.loads = [
        LoadCase().to_dict(),
        LoadCase("tension", 18000).to_dict(),
    ]
if "load_provenance" not in st.session_state:
    st.session_state.load_provenance = "MANUAL_REFERENCE_FORCES"
model_path = ROOT / "models/phase2_surrogate.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
        out = ROOT / "runs/ui-phase2" / uuid.uuid4().hex[:12]
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
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/run_job.py"), str(out / "job.json")],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        log.close()
        st.session_state.process = process
        st.session_state.job_dir = str(out)
        st.success(
            f"Job {out.name} started. Frozen inputs saved; use Refresh job status."
        )
    except Exception as exc:
        st.error(str(exc))


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
            st.sidebar.error(result.get("error", "Analysis failed; review log"))
    else:
        st.sidebar.info(
            "Job running"
            if st.session_state.process.poll() is None
            else "Job exited without a result; inspect log"
        )
    with st.sidebar.expander("Job log"):
        log = out / "background.log"
        if log.exists():
            st.code(log.read_text(encoding="utf-8", errors="replace")[-5000:])


job_status()

if section == "Dashboard":
    st.subheader("From geometry to defensible decisions")
    st.markdown(
        "**FreeCAD solid → Gmsh mesh → CalculiX fields → grouped ML evaluation → constrained optimization → independent verification**"
    )
    cfg = configuration()
    cols = st.columns(4)
    cols[0].metric("Geometry", "Filleted v2")
    cols[1].metric("Boundary model", "Cosine bearing")
    pf = ROOT / "runs/preflight/preflight.json"
    cols[2].metric(
        "Executed preflight",
        "Ready" if pf.exists() and read(pf).get("ready") else "Not verified",
    )
    cols[3].metric(
        "Active model",
        read(model_path)["selected_model"] if model_path.exists() else "Not trained",
    )
    st.caption(
        GEOMETRY_VERSION
        + " | Prescribed compressive pressure, not a nonlinear contact solution."
    )
    data = ROOT / "data/phase2/coarse/manifest.json"
    if data.exists():
        st.json(read(data))
    st.info(
        "Phase 1 historical result: 734.577 g → 384.418 g (47.668%). Sharp pockets, clamped bore, manual loads and mesh-dependent verification. This is not a Phase 2 optimum."
    )
    conv = ROOT / "runs/focused-refinement/convergence.json"
    if conv.exists():
        st.json(read(conv))
    else:
        st.warning("Peak-stress convergence has not been established.")
    pilot = ROOT / "runs/bearing-pilot/geometry.stl"
    if not pilot.exists():
        pilot = ROOT / "evidence/phase2/baseline.stl"
    if pilot.exists():
        st.plotly_chart(cad_figure(pilot), width="stretch")

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
    st.json(st.session_state.geometry)
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
                st.json(metadata)
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
                e = Engine(bore, stroke, rod, rpm, mass, cycle)
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
                st.error(str(exc))
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
    st.subheader(
        "Constrained CAD-mass optimization"
        if optimization
        else "Linear elastic simulation"
    )
    st.caption("Active loads: " + st.session_state.load_provenance)
    st.json(st.session_state.loads)
    with st.form("simulation"):
        material = st.selectbox("Material", list(MATERIALS))
        a, b = st.columns(2)
        size = a.selectbox(
            "Maximum mesh size (mm)", [4.0, 2.5, 1.75, 1.25, 1.0, 5.0, 6.0]
        )
        bc = b.selectbox(
            "Boundary conditions", ["COSINE_BEARING", "LEGACY_CLAMPED_BORE"]
        )
        local = st.checkbox(
            "Local refinement around transitions and pockets", value=True
        )
        strategy = st.selectbox(
            "Local mesh strategy",
            ["Focused junctions and pocket corners", "All CAD curves"],
        )
        local_size = st.number_input(
            "Focused target size (mm)",
            min_value=0.25,
            max_value=float(size),
            value=min(1.25, float(size)),
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
            st.warning(
                "Observed residual allowance plus a labelled heuristic 1.2 stress guard. Local multistart SLSQP is not a global optimum certificate. Final FEA pass remains provisional until convergence is established."
            )
            st.caption(
                "Model: "
                + (
                    read(model_path)["selected_model"]
                    if model_path.exists()
                    else "Phase 2 model unavailable"
                )
            )
        else:
            selection = st.selectbox("Load cases", ["Both", "compression", "tension"])
        submitted = st.form_submit_button(
            "Run Optimization" if optimization else "Run FEA"
        )
    if submitted:
        if optimization and not model_path.exists():
            st.error("Train the compatible Phase 2 model first.")
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
                    if local and strategy.startswith("Focused")
                    else None,
                ),
                MATERIALS[material],
                Constraints(fos, disp) if optimization else Constraints(),
            )
            st.session_state.loads = original

elif section == "Results & Comparison":
    st.subheader("Solver evidence, not surrogate contours")
    paths = (
        sorted((ROOT / "runs").rglob("result.json")) if (ROOT / "runs").exists() else []
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
            st.caption(str(result["load"]) + " | " + str(result["mesh"]))
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
            with st.expander("Hotspot and equilibrium"):
                st.json(
                    {
                        k: result.get(k)
                        for k in ["hotspot", "boundary_conditions", "mesh_quality"]
                    }
                )
        else:
            st.error(result.get("error", "No structural response available"))
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
                st.json(read(path).get("geometry", {}))
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
    optimization = ROOT / "runs/phase2-optimization/optimization.json"
    if optimization.exists():
        st.subheader("New optimization outcome")
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
                            k: d.get(k)
                            for k in ["success", "iterations", "objective", "message"]
                        }
                        for d in diagnostics
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
        with st.expander("Constraints, candidate FEA, margins and full diagnostics"):
            st.json(outcome)
        diagnostic = ROOT / "runs/phase2-diagnostic-verification/verification.json"
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

elif section == "Model Analytics":
    st.subheader("Geometry-grouped held-out evaluation")
    if model_path.exists():
        md = read(model_path)
        st.write("Selected model: " + md["selected_model"])
        st.dataframe(pd.json_normalize(md["comparisons"]).T)
        st.json(
            {
                k: md.get(k)
                for k in [
                    "sample_count",
                    "split_counts",
                    "groups_disjoint",
                    "near_constraint_test_count",
                    "near_constraint_metrics",
                    "mesh_configuration",
                    "residual_margin",
                    "margin_claim",
                ]
            }
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
    else:
        st.info("No compatible Phase 2 model trained yet. Phase 1 labels are excluded.")
    multifidelity = ROOT / "data/phase2/multifidelity.json"
    if multifidelity.exists():
        st.json(read(multifidelity))

elif section == "Reports & Downloads":
    st.subheader("Reproduce and inspect")
    docs = sorted((ROOT / "docs").glob("*.md"))
    document = st.selectbox("Engineering report", docs, format_func=lambda p: p.name)
    st.markdown(document.read_text(encoding="utf-8"))
    st.download_button(
        "Download report", document.read_bytes(), document.name, "text/markdown"
    )
    files = [
        p
        for p in (ROOT / "runs").rglob("*")
        if p.is_file()
        and p.suffix.lower()
        in (".stl", ".step", ".fcstd", ".csv", ".json", ".inp", ".html", ".log")
    ]
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
