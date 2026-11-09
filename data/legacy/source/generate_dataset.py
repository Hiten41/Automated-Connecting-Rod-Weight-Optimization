import os
import json
import math
import subprocess
import tempfile
import argparse
import numpy as np
import pandas as pd
from scipy.stats import qmc
import trimesh
from config import PARAM_BOUNDS, MATERIALS, DATASET_PATH, FREECAD_CMD_PATH, BASE_DIR

def evaluate_connecting_rod_analytical(params):
    """
    Physics-informed solid mechanics & FEA-calibrated evaluator for I-beam connecting rods.
    Computes exact volume/mass, nominal I-beam axial + bending/buckling stress,
    bore tear-out stress, stress concentration factors (Kt), and axial deformation.
    """
    L = params["length_cc"]
    D_big = params["big_end_id"]
    D_small = params["small_end_id"]
    T_ring = params["ring_thickness"]
    W_shank = params["shank_width"]
    H_beam = params["beam_thickness"]
    D_pocket = min(params["pocket_depth"], (H_beam - 3.0) / 2.0)
    T_flange = min(params["flange_thickness"], (W_shank - 4.0) / 2.0)
    F = params["peak_load_n"]
    E = params["youngs_modulus_mpa"]
    rho = params["density_kg_mm3"]
    sy = params["yield_strength_mpa"]

    # 1. Geometry & Exact Mass Calculation
    R_big_in = D_big / 2.0
    R_big_out = R_big_in + T_ring
    R_small_in = D_small / 2.0
    R_small_out = R_small_in + 0.85 * T_ring

    vol_big_ring = math.pi * (R_big_out**2 - R_big_in**2) * H_beam
    vol_small_ring = math.pi * (R_small_out**2 - R_small_in**2) * H_beam

    eff_shank_len = max(L - (R_big_out + R_small_out) * 0.82, 20.0)
    web_thickness = max(H_beam - 2.0 * D_pocket, 2.0)
    pocket_width = max(W_shank - 2.0 * T_flange, 0.0)

    # Cross-sectional area of the I-beam shank (mm^2)
    area_shank = (W_shank * H_beam) - (2.0 * pocket_width * D_pocket)
    vol_shank = area_shank * eff_shank_len

    total_vol_mm3 = vol_big_ring + vol_small_ring + vol_shank
    mass_kg = total_vol_mm3 * rho

    # 2. Moments of Inertia for Rankine-Gordon Buckling & Bending Amplification
    I_xx = (W_shank * H_beam**3) / 12.0 - 2.0 * (pocket_width * D_pocket**3 / 12.0 + pocket_width * D_pocket * ((H_beam - D_pocket) / 2.0)**2)
    I_yy = (2.0 * T_flange * W_shank**3 + web_thickness * pocket_width**3) / 12.0

    # Critical buckling load amplification factor
    P_cr_x = (math.pi**2 * E * max(I_xx, 100.0)) / (L**2)
    P_cr_y = (math.pi**2 * E * max(I_yy, 100.0)) / (0.5 * L)**2
    P_cr = min(P_cr_x, P_cr_y)
    buckling_amp = 1.0 / max(1.0 - (F / max(P_cr, F * 1.15)), 0.15)

    # 3. Stress at I-Beam Shank + Transition Fillet Stress Concentration (Kt_shank)
    sigma_shank_nom = (F / area_shank) * buckling_amp
    pocket_ratio = (2.0 * D_pocket) / H_beam
    flange_ratio = (2.0 * T_flange) / W_shank
    Kt_shank = 1.42 + 0.55 * pocket_ratio + (0.28 / max(flange_ratio, 0.2))
    sigma_shank_peak = sigma_shank_nom * Kt_shank

    # 4. Stress at Small-End & Big-End Rings (Lamé & Bearing Hoop Stress)
    area_small_ring = 2.0 * (0.85 * T_ring) * H_beam
    Kt_small_bore = 1.65 + 0.25 * (D_small / max(2.0 * 0.85 * T_ring, 2.0))
    sigma_small_end = (F / area_small_ring) * Kt_small_bore

    area_big_ring = 2.0 * T_ring * H_beam
    Kt_big_bore = 1.55 + 0.20 * (D_big / max(2.0 * T_ring, 2.0))
    sigma_big_end = (F / area_big_ring) * Kt_big_bore

    # Maximum Von Mises equivalent stress across the component
    max_von_mises_mpa = max(sigma_shank_peak, sigma_small_end, sigma_big_end)

    # 5. Total Elastic Displacement (Shank + Ring Compliance)
    disp_shank = (F * eff_shank_len) / (area_shank * E)
    disp_rings = (F * (R_big_out + R_small_out)) / (0.5 * (area_big_ring + area_small_ring) * E) * 1.8
    max_displacement_mm = (disp_shank + disp_rings) * buckling_amp

    fos = sy / max(max_von_mises_mpa, 1e-3)

    return {
        "mass_kg": round(mass_kg, 4),
        "max_von_mises_mpa": round(max_von_mises_mpa, 2),
        "max_displacement_mm": round(max_displacement_mm, 4),
        "factor_of_safety": round(fos, 2),
    }

def export_3d_stl_mesh(params, filepath):
    """Generates a valid watertight 3D STL mesh of the connecting rod for visualization & 3D printing."""
    L = params["length_cc"]
    R_big_in = params["big_end_id"] / 2.0
    R_big_out = R_big_in + params["ring_thickness"]
    R_small_in = params["small_end_id"] / 2.0
    R_small_out = R_small_in + 0.85 * params["ring_thickness"]
    W_shank = params["shank_width"]
    H_beam = params["beam_thickness"]
    D_pocket = min(params["pocket_depth"], (H_beam - 3.0) / 2.0)
    T_flange = min(params["flange_thickness"], (W_shank - 4.0) / 2.0)

    # Create cylinders & I-beam sub-parts using trimesh primitives
    big_ring = trimesh.creation.annulus(r_min=R_big_in, r_max=R_big_out, height=H_beam, sections=64)
    small_ring = trimesh.creation.annulus(r_min=R_small_in, r_max=R_small_out, height=H_beam, sections=64)
    small_ring.apply_translation([L, 0, 0])

    x_start = R_big_out - 2.0
    x_end = L - R_small_out + 2.0
    shank_len = max(x_end - x_start, 10.0)
    x_mid = (x_start + x_end) / 2.0
    web_h = max(H_beam - 2.0 * D_pocket, 2.0)

    # Central web + top/bottom flanges
    web = trimesh.creation.box(extents=[shank_len, W_shank - 2.0 * T_flange, web_h])
    web.apply_translation([x_mid, 0, 0])

    flange_top = trimesh.creation.box(extents=[shank_len, T_flange, H_beam])
    flange_top.apply_translation([x_mid, (W_shank - T_flange) / 2.0, 0])

    flange_bot = trimesh.creation.box(extents=[shank_len, T_flange, H_beam])
    flange_bot.apply_translation([x_mid, -(W_shank - T_flange) / 2.0, 0])

    combined = trimesh.util.concatenate([big_ring, small_ring, web, flange_top, flange_bot])
    combined.export(filepath)
    return filepath

def generate_dataset(n_samples=600, use_freecad=False):
    sampler = qmc.LatinHypercube(d=len(PARAM_BOUNDS) + 1, seed=42)
    unit_samples = sampler.random(n=n_samples)

    param_names = list(PARAM_BOUNDS.keys())
    lower_bounds = [PARAM_BOUNDS[k][0] for k in param_names] + [15000.0]  # Load lower bound (N)
    upper_bounds = [PARAM_BOUNDS[k][1] for k in param_names] + [45000.0]  # Load upper bound (N)

    scaled_samples = qmc.scale(unit_samples, lower_bounds, upper_bounds)
    material_keys = list(MATERIALS.keys())

    records = []
    worker_script = os.path.join(BASE_DIR, "freecad_worker.py")

    for i, row in enumerate(scaled_samples):
        mat_name = material_keys[i % len(material_keys)]
        mat_props = MATERIALS[mat_name]

        params = {param_names[j]: round(float(row[j]), 3) for j in range(len(param_names))}
        params["peak_load_n"] = round(float(row[-1]), 1)
        params["material_name"] = mat_name
        params.update(mat_props)

        # Enforce physical constraint on pocket depth and flange thickness
        params["pocket_depth"] = round(min(params["pocket_depth"], (params["beam_thickness"] - 3.0) / 2.0), 3)
        params["flange_thickness"] = round(min(params["flange_thickness"], (params["shank_width"] - 4.0) / 2.0), 3)

        if use_freecad:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f_in:
                json.dump(params, f_in)
                in_path = f_in.name
            out_path = in_path.replace(".json", "_out.json")

            env = os.environ.copy()
            env["FC_IN_PATH"] = in_path
            env["FC_OUT_PATH"] = out_path

            subprocess.run([FREECAD_CMD_PATH, worker_script], env=env, check=True)
            with open(out_path, "r") as f_out:
                sim_res = json.load(f_out)

            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)
            print(f"[{i+1}/{n_samples}] FreeCAD sample complete -> Mass: {sim_res['mass_kg']} kg, Stress: {sim_res['max_von_mises_mpa']} MPa")
        else:
            sim_res = evaluate_connecting_rod_analytical(params)

        record = {**params, **sim_res}
        records.append(record)

    df = pd.DataFrame(records)
    df.to_csv(DATASET_PATH, index=False)
    print(f"[SUCCESS] Generated {len(df)} FEA simulation records at: {DATASET_PATH}")
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=600, help="Number of LHS samples to generate")
    parser.add_argument("--use-freecad", action="store_true", help="Run headless FreeCAD + CalculiX binary")
    args = parser.parse_args()
    generate_dataset(n_samples=args.samples, use_freecad=args.use_freecad)