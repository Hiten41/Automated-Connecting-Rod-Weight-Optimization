# Phase 2 ML evaluation

Historical 120 Phase 1 analyses are excluded from Phase 2 training. Geometry/BC/fidelity/version mismatch raises an error. Radius is fixed 1 mm; five other section dimensions vary. Learned targets use exact linear-static stress/F and displacement*E/F scaling to remove known load/modulus dependence. Geometry groups prevent related compression/tension cases leaking across splits.

Dataset: 120 actual solver analyses. Split {'train': 72, 'validation': 24, 'test': 24}; selected mlp. Group separation: True.

## ridge

- max_von_mises_mpa: MAE 139.88, RMSE 176.559, R² 0.927453.
- max_displacement_mm: MAE 0.14324, RMSE 0.185698, R² 0.836736.

## extra_trees

- max_von_mises_mpa: MAE 145.436, RMSE 185.471, R² 0.919944.
- max_displacement_mm: MAE 0.062641, RMSE 0.0966484, R² 0.955775.

## mlp

- max_von_mises_mpa: MAE 28.7433, RMSE 41.5103, R² 0.99599.
- max_displacement_mm: MAE 0.0145794, RMSE 0.0206051, R² 0.99799.

## analytical_nominal_screening

- max_von_mises_mpa: MAE 1082.03, RMSE 1253.72, R² -2.65801.
- max_displacement_mm: MAE 0.458444, RMSE 0.617999, R² -0.808222.

Near-constraint test count: 6; metrics: {'max_von_mises_mpa': {'MAE': 20.302694875877666, 'RMSE': 23.33633121406941, 'R2': 0.9904804461135376}, 'max_displacement_mm': {'MAE': 0.004492162051473419, 'RMSE': 0.004944405009537216, 'R2': 0.997379183900376}}. Sparse coverage is not proof of accurate feasibility-boundary prediction. Observed residual allowance [41.354871222562906, 0.12295013066798077] is not calibrated confidence. The1.2 multiplier remains a labelled heuristic. Coarse8 mm training is not converged truth.

## Paired-fidelity investigation

```json
{
  "status": "EXPLORATORY_SMALL_SAMPLE",
  "coarse_mesh_mm": 8,
  "fine_mesh_mm": 4,
  "coarse_train_cases": 32,
  "fine_train_cases": 4,
  "held_out_fine_cases": 4,
  "held_out_geometry_groups": [
    34,
    22
  ],
  "geometry_leakage": false,
  "coarse_prediction_on_fine": {
    "max_von_mises_mpa": {
      "MAE": 99.70016112494483,
      "RMSE": 109.59368875167524,
      "R2": 0.9146369238355451
    },
    "max_displacement_mm": {
      "MAE": 0.3793317592077799,
      "RMSE": 0.38991816981142235,
      "R2": 0.1489411911852777
    }
  },
  "additive_ridge_correction_on_fine": {
    "max_von_mises_mpa": {
      "MAE": 99.55070763894561,
      "RMSE": 113.5450202617204,
      "R2": 0.9083705348347519
    },
    "max_displacement_mm": {
      "MAE": 0.17323626939292291,
      "RMSE": 0.20301336362894182,
      "R2": 0.7692924122810676
    }
  },
  "mean_fine_minus_coarse": {
    "max_von_mises_mpa": 59.81366271166119,
    "max_displacement_mm": 0.01259950656835562
  },
  "selected_for_optimization": false,
  "limitation": "Two held-out geometry groups only. 4mm is finer than 8mm, not independently converged. Correction is not promoted from this small investigation.",
  "coarse_source": "data\\phase2\\initial36\\verified.jsonl",
  "coarse_sha256": "ba3fe87b74dc08ad5534772edeb76782ba27f73b1acd9158c51ffe90080bb199"
}
```

The correction is not promoted to optimization based on this small test.
