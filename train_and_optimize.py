import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from scipy.optimize import minimize
from config import DATASET_PATH, SURROGATE_MODEL_PATH, PARAM_BOUNDS, MATERIALS
from generate_dataset import generate_dataset, evaluate_connecting_rod_analytical

FEATURE_COLS = [
    "length_cc",
    "big_end_id",
    "small_end_id",
    "ring_thickness",
    "shank_width",
    "beam_thickness",
    "pocket_depth",
    "flange_thickness",
    "peak_load_n",
    "youngs_modulus_mpa",
    "density_kg_mm3",
    "yield_strength_mpa",
]

TARGET_COLS = [
    "mass_kg",
    "max_von_mises_mpa",
    "max_displacement_mm",
]

def train_surrogate_model():
    if not os.path.exists(DATASET_PATH):
        print("[INFO] Dataset not found. Generating 600 LHS simulation samples first...")
        generate_dataset(n_samples=600, use_freecad=False)

    df = pd.read_csv(DATASET_PATH)
    X = df[FEATURE_COLS].values
    y = df[TARGET_COLS].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()

    X_train_s = scaler_X.fit_transform(X_train)
    X_test_s = scaler_X.transform(X_test)
    y_train_s = scaler_y.fit_transform(y_train)

    # Deep Multi-Output Neural Network Surrogate
    nn_model = MLPRegressor(
        hidden_layer_sizes=(128, 128, 64),
        activation="relu",
        solver="adam",
        learning_rate_init=0.002,
        max_iter=800,
        random_state=42,
    )
    nn_model.fit(X_train_s, y_train_s)

    y_pred_s = nn_model.predict(X_test_s)
    y_pred = scaler_y.inverse_transform(y_pred_s)

    metrics = {}
    for idx, col in enumerate(TARGET_COLS):
        metrics[col] = {
            "R2": round(float(r2_score(y_test[:, idx], y_pred[:, idx])), 4),
            "MAE": round(float(mean_absolute_error(y_test[:, idx], y_pred[:, idx])), 4),
        }

    bundle = {
        "model": nn_model,
        "scaler_X": scaler_X,
        "scaler_y": scaler_y,
        "feature_cols": FEATURE_COLS,
        "target_cols": TARGET_COLS,
        "metrics": metrics,
    }
    joblib.dump(bundle, SURROGATE_MODEL_PATH)
    print(f"[SUCCESS] Saved Neural Network Surrogate Model to: {SURROGATE_MODEL_PATH}")
    for k, v in metrics.items():
        print(f"  -> {k}: R² = {v['R2']}, MAE = {v['MAE']}")
    return bundle

def load_or_train_surrogate():
    if not os.path.exists(SURROGATE_MODEL_PATH):
        return train_surrogate_model()
    return joblib.load(SURROGATE_MODEL_PATH)

def predict_with_surrogate(bundle, full_params_dict):
    x_vec = np.array([[full_params_dict[col] for col in FEATURE_COLS]])
    x_scaled = bundle["scaler_X"].transform(x_vec)
    y_scaled = bundle["model"].predict(x_scaled)
    y_pred = bundle["scaler_y"].inverse_transform(y_scaled)[0]

    mass_kg = max(float(y_pred[0]), 0.05)
    vm_stress = max(float(y_pred[1]), 1.0)
    disp_mm = max(float(y_pred[2]), 0.0001)
    fos = full_params_dict["yield_strength_mpa"] / vm_stress

    return {
        "mass_kg": round(mass_kg, 4),
        "max_von_mises_mpa": round(vm_stress, 2),
        "max_displacement_mm": round(disp_mm, 4),
        "factor_of_safety": round(fos, 2),
    }

def optimize_connecting_rod(
    length_cc=145.0,
    big_end_id=50.0,
    small_end_id=24.0,
    peak_load_n=28000.0,
    material_name="Forged Steel (AISI 4340)",
    min_fos=1.8,
    max_disp_limit_mm=0.35,
):
    """
    Uses the trained AI surrogate model + multi-start SLSQP optimization to find the lightest
    connecting rod geometry that satisfies the Factor of Safety and displacement limits.
    """
    bundle = load_or_train_surrogate()
    mat = MATERIALS[material_name]
    max_allowable_stress = mat["yield_strength_mpa"] / min_fos

    # 5 Optimizable Design Variables:
    # x = [ring_thickness, shank_width, beam_thickness, pocket_depth, flange_thickness]
    opt_keys = ["ring_thickness", "shank_width", "beam_thickness", "pocket_depth", "flange_thickness"]
    bounds = [PARAM_BOUNDS[k] for k in opt_keys]

    # Baseline heavy solid-style design (for comparison)
    baseline_params = {
        "length_cc": length_cc,
        "big_end_id": big_end_id,
        "small_end_id": small_end_id,
        "ring_thickness": 8.0,
        "shank_width": 25.0,
        "beam_thickness": 22.0,
        "pocket_depth": 2.2,
        "flange_thickness": 5.5,
        "peak_load_n": peak_load_n,
        "material_name": material_name,
        **mat,
    }
    baseline_perf = evaluate_connecting_rod_analytical(baseline_params)

    def build_param_dict(x):
        return {
            "length_cc": length_cc,
            "big_end_id": big_end_id,
            "small_end_id": small_end_id,
            "ring_thickness": float(x[0]),
            "shank_width": float(x[1]),
            "beam_thickness": float(x[2]),
            "pocket_depth": float(x[3]),
            "flange_thickness": float(x[4]),
            "peak_load_n": peak_load_n,
            "material_name": material_name,
            **mat,
        }

    # Objective: Minimize Mass predicted by Neural Network Surrogate
    def objective(x):
        p = build_param_dict(x)
        pred = predict_with_surrogate(bundle, p)
        return pred["mass_kg"]

    # Constraints (must be >= 0 for SLSQP)
    constraints = [
        # 1. Von Mises Stress <= Allowable Stress
        {"type": "ineq", "fun": lambda x: max_allowable_stress - predict_with_surrogate(bundle, build_param_dict(x))["max_von_mises_mpa"]},
        # 2. Displacement <= Max Limit
        {"type": "ineq", "fun": lambda x: max_disp_limit_mm - predict_with_surrogate(bundle, build_param_dict(x))["max_displacement_mm"]},
        # 3. Geometric feasibility: Web thickness >= 3.5 mm (beam_thickness - 2*pocket_depth >= 3.5)
        {"type": "ineq", "fun": lambda x: x[2] - 2.0 * x[3] - 3.5},
        # 4. Geometric feasibility: Pocket width >= 4.0 mm (shank_width - 2*flange_thickness >= 4.0)
        {"type": "ineq", "fun": lambda x: x[1] - 2.0 * x[4] - 4.0},
    ]

    best_res = None
    best_mass = float("inf")
    rng = np.random.default_rng(42)

    # Multi-start gradient optimization across the Neural Network surrogate surface
    for _ in range(12):
        x0 = [rng.uniform(low, high) for (low, high) in bounds]
        res = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 150})
        if res.success and res.fun < best_mass:
            best_mass = res.fun
            best_res = res

    opt_x = best_res.x if best_res is not None else [6.0, 19.0, 17.0, 4.5, 3.8]
    opt_params = build_param_dict(opt_x)
    for k in opt_keys:
        opt_params[k] = round(opt_params[k], 2)

    # Verify with both AI Surrogate and FEA Analytical Evaluator
    ai_pred = predict_with_surrogate(bundle, opt_params)
    fea_verified = evaluate_connecting_rod_analytical(opt_params)

    mass_reduction_pct = ((baseline_perf["mass_kg"] - fea_verified["mass_kg"]) / baseline_perf["mass_kg"]) * 100.0

    return {
        "optimized_geometry": opt_params,
        "ai_prediction": ai_pred,
        "fea_verification": fea_verified,
        "baseline_performance": baseline_perf,
        "baseline_geometry": baseline_params,
        "mass_reduction_pct": round(mass_reduction_pct, 2),
        "surrogate_metrics": bundle["metrics"],
    }

if __name__ == "__main__":
    train_surrogate_model()
    result = optimize_connecting_rod()
    print("\n--- AI OPTIMIZATION SUMMARY ---")
    print(f"Baseline Mass:  {result['baseline_performance']['mass_kg']} kg")
    print(f"Optimized Mass: {result['fea_verification']['mass_kg']} kg ({result['mass_reduction_pct']}% reduction)")
    print(f"Optimized Stress: {result['fea_verification']['max_von_mises_mpa']} MPa (FoS: {result['fea_verification']['factor_of_safety']})")