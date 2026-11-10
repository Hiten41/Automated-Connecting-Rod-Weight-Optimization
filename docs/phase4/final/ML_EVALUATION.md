# Machine-learning evaluation

## Dataset and split

`data/phase4/fea-dataset.jsonl` contains 86 provenance-preserving solver records: 60 coarse load-case rows from 30 distinct CAD geometries and 26 refined load-case rows across six refined geometries. It records family, parameters, CAD mass, load, boundary model, mesh fidelity/settings, stress, displacement, FoS, solver status/version, geometry hash, sample ID and raw result/field paths. Mesh levels and paired load cases are repeated observations, not independent geometry samples.

Three model families were compared using the same numeric geometry/load features and one-hot family/load indicators:

| Evaluation | Model | MAE (MPa) | RMSE (MPa) | R² |
|---|---|---:|---:|---:|
| 5-fold geometry-grouped out-of-fold coarse screen | Ridge | 168.5 | 238.4 | 0.449 |
|  | Extra Trees | 173.8 | 263.1 | 0.330 |
|  | MLP | 136.3 | 199.5 | 0.614 |
| Coarse-trained, geometry-held-out refined test (6 geometries, 12 load rows) | Ridge | 114.4 | 169.3 | −2.720 |
|  | Extra Trees | 69.0 | 90.7 | −0.068 |
|  | MLP | 104.7 | 117.9 | −0.804 |

The fine test intentionally excludes each refined geometry from coarse training. It also changes mesh fidelity, so these scores measure combined geometry and fidelity generalization. The holdout has only six distinct geometries and is too small to validate a surrogate. The MLP also reached its iteration limit in the grouped run. The historical Phase 3 MLP was worse still (MAE about 208.86 MPa, R² about 0.031 on its held-out evaluation).

![Grouped ML diagnostics](figures/phase4-ml-model-comparison.png)

## Decision

No model is used to enforce constraints, choose a final feasible design, or replace CalculiX. The best model’s fine-holdout MAE (Extra Trees, 69.0 MPa) exceeds P4-0065’s 28.44 MPa tension headroom to the allowable; its fine-holdout R² is negative. FEA remains mandatory for all final claims. The generated dataset supports future research but does not support a constraint-authoritative surrogate.
