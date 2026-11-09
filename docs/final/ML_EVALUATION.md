# Machine learning evaluation

## Phase 3 dataset and split

Training uses the 24 fine-fidelity cases (12 distinct geometries × compression/tension) from the deterministic Phase 3 dataset. All load cases for one geometry stay in one partition. Seed 42 produced 12 train, 6 validation and 6 test analyses across 6, 3 and 3 held-out geometry groups respectively; groups are disjoint. The 1% normalized-distance union rule found 12 geometry groups. The dataset is fixed at 4 mm bulk / 0.75 mm big-end transition refinement and uses the same geometry, material and cosine-bearing load model throughout.

The output artifact is `models/phase3_surrogate.joblib`; its portable evaluation record, grouped IDs and configuration are in `models/phase3_surrogate.json`. Held-out predictions and residuals are in `models/phase3_surrogate.test.csv`; the saved image is `models/phase3_surrogate.evaluation.png`. A model is marked `EXPLORATORY_SCREENING_ONLY` by default. The Phase 3 optimizer API and app reject such a model for optimization unless an adequately supported model has been explicitly accepted.

## Held-out comparison

The MLP was selected on validation normalized error. Test metrics below use only the six held-out analyses (three geometries), so R² and error estimates are highly uncertain.

| Model | Stress MAE (MPa) | Stress RMSE (MPa) | Stress R² | Displacement MAE (mm) | Displacement RMSE (mm) | Displacement R² |
|---|---:|---:|---:|---:|---:|---:|
| Ridge | 313.61 | 394.19 | −0.766 | 0.12647 | 0.15629 | −0.026 |
| Extra Trees | 354.58 | 360.43 | −0.477 | 0.09859 | 0.10124 | 0.569 |
| MLP, selected on validation | 208.86 | 291.95 | 0.031 | 0.06572 | 0.09773 | 0.599 |
| Analytical nominal screening | 733.91 | 795.09 | −6.186 | 0.24096 | 0.29002 | −2.535 |

The nominal analytical response is not a local stress predictor and is included only as a baseline. The MLP training stress MAE is 10.29 MPa and training R² is 0.999, while test stress MAE rises to 208.86 MPa and R² falls to 0.031. Its validation stress MAE is 79.75 MPa. This generalization gap and the poor test result reject optimization use despite the validation selection score. Test residuals are mostly stress overpredictions, but one of six stress estimates is low; the sign and magnitude are not reliable enough for a safety margin.

Only two test analyses meet the exploratory near-constraint rule (FoS 1.4–2.2 or displacement 0.28–0.42 mm). On these two, stress MAE is 56.29 MPa, RMSE 77.32 MPa and R² −0.495; displacement MAE is 0.03111 mm, RMSE 0.03217 mm and R² −0.410. This sample is too small to validate boundary prediction. The maximum observed validation underprediction margin is stored as 142.30 MPa stress / 0.03952 mm displacement; it is not a calibrated confidence bound and does not cover held-out groups.

## Fidelity comparison and decision

The paired 6, 1.25 and 0.75 mm responses show substantial design-dependent mesh effects. From intermediate to fine, the median stress increase is 4.67% in compression (range −2.31% to +29.76%) and 6.60% in tension (−4.66% to +31.68%). Displacement changes are smaller, but this does not validate stress. A multi-fidelity correction was not fitted: 12 geometry groups are insufficient to establish transfer behavior, and the coarser labels are not treated as truth for the fine response.

**Decision: Phase 3 ML evaluation is complete as a negative acceptance result.** The comparison and grouped holdout are reproducible, but the model is not accepted for optimization or structural decisions. The optimizer is guarded against this exploratory artifact. No optimizer run or candidate acceptance is claimed; use actual CAD/FEA and expand geometry diversity before reconsidering model-assisted optimization. The earlier Phase 2 MLP remains a separate model trained on 8 mm labels and is not a converged-stress predictor.
