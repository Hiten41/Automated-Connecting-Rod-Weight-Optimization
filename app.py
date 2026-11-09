"""Engineering UI. Explicit submissions launch background CLI jobs."""

import json
import subprocess
import sys
import uuid
from pathlib import Path
import pandas as pd
import streamlit as st
from conrod.schemas import Geometry, LoadCase, Constraints, MeshSettings
from conrod.materials import MATERIALS
from conrod.analytical import evaluate
from conrod.fea import configuration, ROOT
from conrod.visualization import cad_figure, solver_field_figure

st.set_page_config(page_title="Connecting Rod | Validated Design Lab", layout="wide")
st.title("Connecting Rod Design Lab")
st.caption(
    "AI-driven generative design and FEA-based lightweight optimization • Bhagavat Pratim Das & Hiten Arora"
)
st.info(
    "Research prototype · Linear-elastic static analysis · Academic bore clamp/traction boundary conditions · No fatigue, contact, thermal or nonlinear buckling certification"
)
tabs = st.tabs(
    [
        "Overview",
        "Design inputs & run",
        "Geometry & results",
        "Design exploration",
        "Exports",
    ]
)
with tabs[0]:
    st.subheader("A traceable engineering pipeline")
    st.markdown(
        "**FreeCAD solid → Gmsh mesh → CalculiX fields → verified dataset → surrogate → constrained optimization → independent FEA**"
    )
    cfg = configuration()
    a, b, c = st.columns(3)
    a.metric(
        "FreeCAD runtime",
        "Configured"
        if Path(cfg.get("freecad_python") or "_missing").is_file()
        else "Unavailable",
    )
    b.metric(
        "CalculiX",
        "Configured" if Path(cfg.get("ccx") or "_missing").is_file() else "Unavailable",
    )
    model = ROOT / "models/fea_surrogate.json"
    c.metric("FEA surrogate", "Available" if model.exists() else "Not trained")
    if model.exists():
        meta = json.loads(model.read_text())
        st.write(
            f"Model: {meta['selected_model']} · {meta['sample_count']} solver analyses · Dataset SHA256: {meta['dataset_sha256'][:16]}"
        )
        st.warning(
            "Residual margins are observed validation errors, not calibrated confidence. Predictions are restricted to the measured input ranges."
        )
    st.markdown(
        "Legacy data remains archived: **300 analytical-response records, zero verified CalculiX records**. It is excluded from FEA training."
    )
    report = ROOT / "docs/VALIDATION_REPORT.md"
    if report.exists():
        with st.expander("Validation record"):
            st.markdown(report.read_text(encoding="utf-8"))
with tabs[1]:
    st.subheader("Design conditions")
    with st.form("design"):
        left, right = st.columns(2)
        with left:
            length = st.number_input("Center distance (mm)", 125.0, 165.0, 145.0)
            big = st.number_input("Big bore diameter (mm)", 44.0, 56.0, 50.0)
            small = st.number_input("Small bore diameter (mm)", 20.0, 28.0, 24.0)
            material_name = st.selectbox("Material", list(MATERIALS))
            compression = st.number_input(
                "Compression load (N)", 15000.0, 45000.0, 28000.0, 500.0
            )
            tension = st.number_input(
                "Tension load (N)", 15000.0, 45000.0, 18000.0, 500.0
            )
        with right:
            fos = st.number_input(
                "Minimum yield factor of safety", 1.25, 3.0, 1.8, 0.05
            )
            disp = st.number_input("Maximum displacement (mm)", 0.05, 1.0, 0.35, 0.05)
            size = st.selectbox("Mesh size (mm)", [1.75, 2.5, 4.0, 5.0])
            action = st.selectbox(
                "Evaluation mode", ["ANALYTICAL", "CAD_ONLY", "FEA", "OPTIMIZE + FEA"]
            )
            st.caption(
                "Baseline dimensions: ring 8, width 25, thickness 22, pocket 2.2, flange 5.5 mm. Optimization changes these five variables."
            )
        submitted = st.form_submit_button("Run selected analysis", type="primary")
    if submitted:
        g = Geometry(length_cc=length, big_end_id=big, small_end_id=small)
        m = MATERIALS[material_name]
        loads = [LoadCase("compression", compression), LoadCase("tension", tension)]
        try:
            g.validate()
            m.validate()
            Constraints(fos, disp).validate()
            if (
                st.session_state.get("process")
                and st.session_state.process.poll() is None
            ):
                st.warning("A job is already running. Wait for completion.")
            elif action == "ANALYTICAL":
                st.session_state.result = dict(
                    status="ANALYTICAL",
                    geometry=g.to_dict(),
                    results=[evaluate(g, m, load_case) for load_case in loads],
                )
                st.session_state.pop("result_path", None)
            else:
                out = ROOT / "runs" / ("ui-" + uuid.uuid4().hex[:10])
                out.mkdir(parents=True)
                job = dict(
                    geometry=g.to_dict(),
                    material=m.to_dict(),
                    loads=[load_case.to_dict() for load_case in loads],
                    constraints=Constraints(fos, disp).__dict__,
                    mesh=MeshSettings(size).to_dict(),
                    action=action,
                    output=str(out),
                )
                (out / "ui-request.json").write_text(json.dumps(job))
                log = open(out / "ui.log", "w")
                proc = subprocess.Popen(
                    [
                        sys.executable,
                        str(ROOT / "scripts/run_job.py"),
                        str(out / "ui-request.json"),
                    ],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                log.close()
                st.session_state.process = proc
                st.session_state.result_path = str(out / "ui-result.json")
                st.session_state.job_dir = str(out)
                st.session_state.pop("result", None)
                st.success(
                    "Started background job. Use Refresh status to check progress."
                )
        except Exception as exc:
            st.error(str(exc))
    if "result_path" in st.session_state:
        st.button("Refresh status")
        path = Path(st.session_state.result_path)
        if path.exists():
            st.session_state.result = json.loads(path.read_text())
            st.success("Job finished: " + st.session_state.result["status"])
        elif st.session_state.process.poll() is None:
            st.info(
                "Running CAD / mesh / solver / optimization. Inputs are frozen for this job."
            )
        else:
            st.error("Worker exited without a result. See the job log below.")
        log = Path(st.session_state.job_dir) / "ui.log"
        if log.exists():
            with st.expander("Execution log"):
                st.code(log.read_text(errors="replace")[-6000:])
    if st.button("Load saved reference experiment"):
        p = ROOT / "runs/optimization-guarded/optimization.json"
        if p.exists():
            st.session_state.result = json.loads(p.read_text())
            st.session_state.pop("result_path", None)
        else:
            st.info("No reference optimization has completed yet.")
result = st.session_state.get("result")
with tabs[2]:
    st.subheader("Geometry and numerical provenance")
    if not result:
        st.info("Submit an analysis or load the saved experiment to display results.")
    else:
        status = result["status"]
        st.write("**Status:**", status)
        if status in ("VERIFIED",):
            st.warning(
                "FEA constraints pass at the stated mesh. Peak-stress mesh convergence remains an open engineering limitation; this is not a certified safe production design."
            )
            a, b, c = st.columns(3)
            a.metric(
                "Baseline CAD mass (g)", f"{result['baseline_mass_kg'] * 1000:.2f}"
            )
            b.metric(
                "Optimized CAD mass (g)", f"{result['optimized_mass_kg'] * 1000:.2f}"
            )
            c.metric("Mass reduction", f"{result['mass_reduction_pct']:.2f}%")
            rows = result["result"]["fea"]
            st.write("Constraint margins", result["result"]["margins"])
            st.write("ML predictions (not FEA)", result["result"]["predictions"])
        else:
            rows = result.get("results", [])
        for r in rows:
            st.write(r.get("load", {}).get("kind", "Estimate"), r["status"])
            fields = (
                [
                    "mass_kg",
                    "max_von_mises_mpa",
                    "max_displacement_mm",
                    "factor_of_safety",
                ]
                if r["status"] == "FEA_SUCCESS"
                else [
                    "estimated_nominal_stress_mpa",
                    "estimated_displacement_mm",
                    "estimated_factor_of_safety",
                    "buckling_margin",
                ]
            )
            st.json({k: r[k] for k in fields if k in r})
            if r.get("error"):
                st.error(r["error"])
        cad_rows = [
            r
            for r in rows
            if r.get("output_dir") and (Path(r["output_dir"]) / "geometry.stl").exists()
        ]
        if cad_rows:
            st.plotly_chart(
                cad_figure(Path(cad_rows[0]["output_dir"]) / "geometry.stl"),
                width="stretch",
            )
            st.caption(
                "Neutral CAD tessellation from the authoritative FreeCAD solid. No synthetic stress colors."
            )
        if (
            cad_rows
            and cad_rows[0].get("fields_path")
            and Path(cad_rows[0]["fields_path"]).exists()
        ):
            with st.expander("Actual solver stress samples"):
                st.plotly_chart(
                    solver_field_figure(cad_rows[0]["fields_path"]), width="stretch"
                )
                st.caption(
                    "Element-centroid point cloud: arithmetic mean of actual integration-point von Mises stresses. These are not interpolated surface contours or the reported unaveraged peak."
                )
        elif status == "ANALYTICAL":
            st.caption("Uniform-shank estimates only; no CAD mass or FEA claim.")
        if result.get("error"):
            st.error(result["error"])
        if result.get("baseline_fea"):
            baseline_stl = (
                Path(result["baseline_fea"][0]["output_dir"]) / "geometry.stl"
            )
            if baseline_stl.exists():
                with st.expander("Baseline CAD for comparison"):
                    st.plotly_chart(cad_figure(baseline_stl), width="stretch")
                    st.caption(
                        "Baseline under the same packaging, material, and loads."
                    )
        with st.expander("Full result and diagnostics"):
            st.json(result)
with tabs[3]:
    st.subheader("Verified design space")
    dataset = ROOT / "data/verified/expanded_lhs/verified.jsonl"
    if not dataset.exists():
        dataset = ROOT / "data/verified/pilot/verified.jsonl"
    if dataset.exists():
        rows = [json.loads(s) for s in dataset.read_text().splitlines() if s.strip()]
        frame = pd.DataFrame(rows)
        import plotly.express as px

        frame["case"] = [r["load"]["kind"] for r in rows]
        frame["material"] = [r["material"]["name"] for r in rows]
        st.plotly_chart(
            px.scatter(
                frame,
                x="mass_kg",
                y="max_von_mises_mpa",
                color="material",
                symbol="case",
                labels={
                    "mass_kg": "CAD mass (kg)",
                    "max_von_mises_mpa": "FEA peak stress (MPa)",
                },
            ),
            width="stretch",
        )
        st.caption(
            "Different loads/materials are shown for provenance; this mixed-condition scatter is not a Pareto frontier."
        )
        st.write(f"{len(frame)} verified analyses")
        st.dataframe(
            frame[
                [
                    "mass_kg",
                    "max_von_mises_mpa",
                    "max_displacement_mm",
                    "factor_of_safety",
                    "case",
                    "material",
                ]
            ],
            hide_index=True,
        )
    else:
        st.info("No verified simulation dataset yet.")
    fig = ROOT / "models/fea_surrogate.evaluation.png"
    if fig.exists():
        st.image(str(fig), caption="Held-out prediction and residual plots")
with tabs[4]:
    st.subheader("Exact-design exports")
    validation_doc = ROOT / "docs/VALIDATION_REPORT.md"
    if validation_doc.exists():
        st.download_button(
            "Reproducible validation summary",
            validation_doc.read_bytes(),
            file_name="validation-summary.md",
        )
    if result:
        st.download_button(
            "Result JSON",
            json.dumps(result, indent=2),
            file_name="result.json",
            mime="application/json",
        )
        rows = (
            result["result"]["fea"]
            if result.get("status") == "VERIFIED"
            else result.get("results", [])
        )
        if rows:
            st.download_button(
                "Summary CSV",
                pd.json_normalize(rows)
                .drop(columns=["traceback"], errors="ignore")
                .to_csv(index=False),
                file_name="summary.csv",
                mime="text/csv",
            )
            selected_case = st.selectbox(
                "Export load case",
                range(len(rows)),
                format_func=lambda i: (
                    rows[i].get("load", {}).get("kind", f"Case {i + 1}")
                ),
            )
            r = rows[selected_case]
            if r.get("output_dir"):
                for filename in (
                    "geometry.stl",
                    "geometry.step",
                    "geometry.FCStd",
                    "fields.json",
                    "job.inp",
                    "result.json",
                ):
                    p = Path(r["output_dir"]) / filename
                    if p.exists():
                        st.download_button(
                            "Download " + filename,
                            p.read_bytes(),
                            file_name=filename,
                            key="dl-" + filename,
                        )
    else:
        st.info("Exports become available after an analysis completes.")
