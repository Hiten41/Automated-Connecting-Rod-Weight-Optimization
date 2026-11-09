# Technical audit

Original default branch `main`, commit `11c3681a7bf49423950855f84a730b3843bce804`. Fork: Hiten41/Automated-Connecting-Rod-Weight-Optimization. Work is confined to `feature/validated-rod-optimization`; upstream push URL is disabled. Original file copies remain under `data/legacy/source`; the complete tracked-object inventory is `original-tree.txt`.

| Original file/function | Problem and consequence | Correction | Test/evidence | Status |
|---|---|---|---|---|
| data CSV / worker fallback | 300 SUCCESS_CAD_VERIFIED rows; all stress, displacement and FoS equal analytical evaluator at stored precision, zero SUCCESS_CCX. Mislabelled numerical provenance. | Archived exact CSV/hash, separate verified records, no mixed-fidelity training. | audit-baseline.json; test_dataset.py | Corrected |
| app.py / stress_field | Sinusoid over mesh coordinates looked like a stress contour. | Neutral CAD mesh; explicitly labelled actual solver sample cloud only. | test_no_fabricated_contour; application inspection | Corrected |
| train_and_optimize.py / predict_with_surrogate | Rounded predictions erased small finite-difference gradients. | Full-precision inference; scaled variables and explicit finite-difference step. | test_precision_and_serialization | Corrected |
| train_and_optimize.py / optimize_connecting_rod | Analytical final check, no independent solver verification. | Every selected candidate runs both actual load cases; all constraints rechecked. | test_missing_post_fea_rejected; test_no_invented_optimum | Corrected |
| freecad_worker.py / build_and_simulate | Exceptions silently produced analytical SUCCESS_CAD_VERIFIED. | Explicit ANALYTICAL/CAD_ONLY/FEA modes; diagnostic failure JSON. | test_no_fallback | Corrected |
| generate_dataset.py / export_3d_stl_mesh | Five overlapping/disconnected mesh components, inconsistent with solid. | Single FreeCAD solid drives mesh, STEP/STL and mass. | legacy-assets.json; test_real_cad_and_export_consistency | Corrected |
| generate_dataset.py and freecad_worker.py / I_yy | Incorrect second transverse inertia. | Pocket subtraction and independent rectangle decomposition with defined axes. | test_section_independent_rectangle_decomposition; test_original_inertia_is_wrong | Corrected |
| analytical evaluators / buckling_amp | Capped denominator returned finite response beyond Euler instability; unexplained K=0.5. | K=1 screening, explicit unstable state, no artificial amplification. | test_buckling_rejected | Corrected |
| analytical evaluators / Kt | Empirical multipliers claimed FEA calibration without evidence. | Removed from active mechanics; shank nominal estimates labelled as such. | ENGINEERING_ASSUMPTIONS.md | Corrected |
| CAD worker / face selection | Heuristic area/COM with arbitrary Face1/Face2 fallbacks; ambiguous force direction. | Geometric cylinder matching and explicit signed distributed x force. | test_load_resultant_and_input_field_width; actual INP files | Corrected |
| CAD and sampling / min clamps | Inputs silently changed to fit geometry. | Typed feasibility rejection and LHS rejection sampling. | test_invalid_web_not_clamped; test_invalid_pocket_not_clamped | Corrected |
| optimizer / hardcoded fallback | Unconverged search could invent dimensions and success. | NO_VERIFIED_FEASIBLE_DESIGN with diagnostics; no fabricated optimum. | test_no_invented_optimum | Corrected |
| app.py / top-level optimization | Expensive work and retraining on slider reruns. | Forms, explicit submit, background subprocess, session state, offline training. | Streamlit AppTest | Corrected |
| venv and caches | 17,974 environment files tied to another user's Python installation. | Removed from feature-branch index, ignored; retained in upstream history. | original-tree.txt | Corrected |
| new deck integration | Long near-zero coordinate strings exceeded solver field width, causing negative Jacobians. | Bounded scientific formatting; patch test and regression. | test_load_resultant_and_input_field_width; validation/patch | Corrected |
| sharp pocket / clamp peaks | Mesh-sensitive maxima can affect optimized safety. | Reported refinement studies; no mesh-independent certification claim. | FEA_VALIDATION.md | Open engineering limitation |

The committed model is an MLPRegressor with three outputs trained on the legacy data. Its reported accuracy does not validate CalculiX. Its exact bytes are retained but the active app never loads it. The legacy STL is watertight but consists of five components, proving that watertightness alone did not establish one physical solid.
