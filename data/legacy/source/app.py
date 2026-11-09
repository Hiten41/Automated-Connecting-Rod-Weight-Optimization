import os
import json
import subprocess
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import trimesh

from config import MATERIALS, EXPORT_DIR, DATASET_PATH, FREECAD_CMD_PATH, BASE_DIR
from train_and_optimize import optimize_connecting_rod
from generate_dataset import export_3d_stl_mesh

st.set_page_config(
    page_title="AI Generative Design: Connecting Rod",
    layout="wide",
)

st.title("AI-Driven Generative Design & FEA Lightweight Optimization of an Automobile Connecting Rod")
st.caption("Developed by Bhagavat Pratim Das (24JE0493) & Hiten Arora (24JE0503) | FreeCAD + CalculiX + Neural Network Surrogate Pipeline")

# Sidebar: User Inputs & Constraints
st.sidebar.header("1. Engine Packaging & Load")
length_cc = st.sidebar.slider("Center-to-Center Length (mm)", 125.0, 165.0, 145.0, 1.0)
big_end_id = st.sidebar.slider("Crankpin (Big End) Bore ID (mm)", 44.0, 56.0, 50.0, 0.5)
small_end_id = st.sidebar.slider("Piston Pin (Small End) Bore ID (mm)", 20.0, 28.0, 24.0, 0.5)
peak_load_n = st.sidebar.slider("Peak Combustion/Inertial Load (N)", 15000, 45000, 28000, 500)

st.sidebar.header("2. Material & Safety Constraints")
material_name = st.sidebar.selectbox("Connecting Rod Material", list(MATERIALS.keys()))
min_fos = st.sidebar.slider("Minimum Factor of Safety (FoS)", 1.25, 3.00, 1.80, 0.05)
max_disp_mm = st.sidebar.slider("Max Allowable Elongation (mm)", 0.15, 0.60, 0.35, 0.05)

# Run Optimization
res = optimize_connecting_rod(
    length_cc=length_cc,
    big_end_id=big_end_id,
    small_end_id=small_end_id,
    peak_load_n=float(peak_load_n),
    material_name=material_name,
    min_fos=min_fos,
    max_disp_limit_mm=max_disp_mm,
)

opt_geom = res["optimized_geometry"]
fea_ver = res["fea_verification"]
ai_pred = res["ai_prediction"]
base_perf = res["baseline_performance"]

# Top KPI Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Optimized Mass",
    f"{fea_ver['mass_kg']*1000:.1f} g",
    f"-{res['mass_reduction_pct']:.1f}% vs Baseline ({base_perf['mass_kg']*1000:.1f} g)",
    delta_color="inverse",
)
col2.metric(
    "Max Von Mises Stress",
    f"{fea_ver['max_von_mises_mpa']:.1f} MPa",
    f"AI Predicted: {ai_pred['max_von_mises_mpa']:.1f} MPa",
)
col3.metric(
    "Factor of Safety (FoS)",
    f"{fea_ver['factor_of_safety']:.2f}",
    f"Target >= {min_fos:.2f}",
)
col4.metric(
    "Max Peak Displacement",
    f"{fea_ver['max_displacement_mm']:.4f} mm",
    f"Limit <= {max_disp_mm:.2f} mm",
)

st.divider()

# Main Layout: 3D Interactive Mesh & Optimal Dimensions
left_col, right_col = st.columns([1.35, 1.0])

with left_col:
    st.subheader("Interactive 3D Generative CAD Preview")
    stl_path = os.path.join(EXPORT_DIR, "optimized_connecting_rod.stl")
    export_3d_stl_mesh(opt_geom, stl_path)

    mesh = trimesh.load(stl_path)
    vertices = mesh.vertices
    faces = mesh.faces

    # FIXED: NumPy 2.0 compatible peak-to-peak calculation
    norm_x = (vertices[:, 0] - vertices[:, 0].min()) / (vertices[:, 0].max() - vertices[:, 0].min() + 1e-5)
    stress_field = fea_ver["max_von_mises_mpa"] * (0.45 + 0.55 * np.sin(norm_x * np.pi))

    fig_3d = go.Figure(
        data=[
            go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                intensity=stress_field,
                colorscale="Jet",
                colorbar=dict(title="Von Mises (MPa)"),
                opacity=1.0,
                flatshading=True,
            )
        ]
    )
    fig_3d.update_layout(
        scene=dict(aspectmode="data", xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)"),
        margin=dict(l=0, r=0, b=0, t=10),
        height=440,
    )
    st.plotly_chart(fig_3d, use_container_width=True)

with right_col:
    st.subheader("AI-Synthesized Parametric Dimensions")
    dim_df = pd.DataFrame(
        [
            {"Parameter": "Ring Wall Thickness", "Baseline (mm)": res["baseline_geometry"]["ring_thickness"], "AI Optimized (mm)": opt_geom["ring_thickness"]},
            {"Parameter": "Shank Width (I-Beam)", "Baseline (mm)": res["baseline_geometry"]["shank_width"], "AI Optimized (mm)": opt_geom["shank_width"]},
            {"Parameter": "Beam Extrusion Thickness", "Baseline (mm)": res["baseline_geometry"]["beam_thickness"], "AI Optimized (mm)": opt_geom["beam_thickness"]},
            {"Parameter": "I-Beam Pocket Depth (per side)", "Baseline (mm)": res["baseline_geometry"]["pocket_depth"], "AI Optimized (mm)": opt_geom["pocket_depth"]},
            {"Parameter": "I-Beam Flange Thickness", "Baseline (mm)": res["baseline_geometry"]["flange_thickness"], "AI Optimized (mm)": opt_geom["flange_thickness"]},
        ]
    )
    st.dataframe(dim_df, use_container_width=True, hide_index=True)

    st.subheader("Surrogate Model Accuracy (Test Split)")
    metrics_df = pd.DataFrame(res["surrogate_metrics"]).T.reset_index().rename(columns={"index": "Output Metric"})
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    # Download STL & Trigger FreeCAD STEP Export
    with open(stl_path, "rb") as f_stl:
        st.download_button(
            label="Download Optimized 3D Mesh (.STL)",
            data=f_stl,
            file_name="optimized_connecting_rod.stl",
            mime="application/sla",
            use_container_width=True,
        )

    if st.button("Generate Native FreeCAD (.STEP) File", use_container_width=True):
        step_path = os.path.join(EXPORT_DIR, "optimized_connecting_rod.step")
        json_in = os.path.join(EXPORT_DIR, "cad_job.json")
        json_out = os.path.join(EXPORT_DIR, "cad_out.json")
        job_payload = {**opt_geom, "export_step": step_path, "cad_only": True}
        with open(json_in, "w") as fj:
            json.dump(job_payload, fj)
        try:
            # FIXED: FreeCAD 1.1 Environment Variable passing
            env = os.environ.copy()
            env["FC_IN_PATH"] = json_in
            env["FC_OUT_PATH"] = json_out
            subprocess.run([FREECAD_CMD_PATH, os.path.join(BASE_DIR, "freecad_worker.py")], env=env, check=True)
            st.success(f"Exported STEP file to: {step_path}")
        except Exception as e:
            st.info(f"Saved FreeCAD job config to {json_in}. Ensure FreeCAD is added to PATH ({e}).")

st.divider()

# Bottom Section: Design Space Pareto Chart
st.subheader("Design Space Exploration & Pareto Front (Mass vs. Von Mises Stress)")
if os.path.exists(DATASET_PATH):
    df_data = pd.read_csv(DATASET_PATH)
    fig_pareto = px.scatter(
        df_data,
        x="mass_kg",
        y="max_von_mises_mpa",
        color="material_name",
        hover_data=["shank_width", "beam_thickness", "pocket_depth", "factor_of_safety"],
        labels={"mass_kg": "Mass (kg)", "max_von_mises_mpa": "Max Von Mises Stress (MPa)"},
        opacity=0.65,
    )
    fig_pareto.add_scatter(
        x=[fea_ver["mass_kg"]],
        y=[fea_ver["max_von_mises_mpa"]],
        mode="markers+text",
        marker=dict(size=16, color="red", symbol="star"),
        name="Current AI Optimum",
        text=["AI Optimum"],
        textposition="top center",
    )
    st.plotly_chart(fig_pareto, use_container_width=True)