# Validation and acceptance report

**Overall: reviewable research implementation; full requested acceptance is incomplete.** All four proposal pipeline functions have been demonstrated with real CAD/solver data. Peak-stress mesh convergence remains unresolved, and visual browser QA/screenshots are blocked by the desktop setting. Do not represent this as a production-qualified connecting rod.

## Isolation
Fork: https://github.com/Hiten41/Automated-Connecting-Rod-Weight-Optimization

Branch: `feature/validated-rod-optimization`. Original baseline: `11c3681a7bf49423950855f84a730b3843bce804`. Upstream push URL is disabled. No original-repository write, PR, merge or production deployment has been performed. Final upstream verification is stored in `isolation-final.json`.

## Actual reference experiment
Fixed center distance 145 mm, bores 50/24 mm, nominal AISI 4340 steel, compression 28000 N, tension 18000 N; FoS≥1.8, displacement≤0.35 mm, Euler margin≥1.8. Same conditions and final 1.75 mm verification mesh are used for baseline/candidate.

CAD mass: 734.577 → 384.418 g. Reduction: 47.668%. Optimization plus final/baseline verification elapsed 367.51 s. Three SLSQP starts converged; no global-optimality claim is made. Dimensions are exported at full precision with no manufacturing rounding.

| Case | Predicted stress (MPa) | FEA stress (MPa) | Predicted displacement (mm) | FEA displacement (mm) | FEA FoS |
|---|---|---|---|---|---|
| compression | 290.6924 | 352.9309 | 0.1075186 | 0.1172791 | 2.01173 |
| tension | 200.6112 | 226.9738 | 0.0733456 | 0.0753936 | 3.12811 |

Final geometry (mm):
```json
{
  "length_cc": 145.0,
  "big_end_id": 50.0,
  "small_end_id": 24.0,
  "ring_thickness": 8.12553968714036,
  "shank_width": 27.919505402314122,
  "beam_thickness": 14.0234410862671,
  "pocket_depth": 5.261587306491249,
  "flange_thickness": 3.9309801560844986
}
```

Independent constraint margins: `{"compression_stress_mpa": 41.51352962486976, "compression_displacement_mm": 0.23272085708492915, "compression_buckling": 4.656087284369913, "tension_stress_mpa": 167.47064535532277, "tension_displacement_mm": 0.2746063719732123}`. The Euler screen is an estimate, not a solved buckling mode.

## Tests and application
Commands executed:
```powershell
python -m pytest tests -q --junitxml=docs/test-results.xml
python -m ruff check src scripts tests workers app.py --select E4,E7,E9,F
python scripts/check_environment.py
python scripts/validate_fea.py
python scripts/generate_fea_dataset.py --geometries 60 --seed 44 --output data/verified/expanded_lhs
python scripts/train_surrogate.py --dataset data/verified/expanded_lhs/verified.jsonl
python scripts/run_optimization.py --mesh-size 1.75
python -m streamlit run app.py --server.port 8502
```

37 pytest tests pass, including the external CAD and solver tests; none skipped. Ruff checks pass. Streamlit AppTest covers initial render, analytical submission, actual background CAD completion, saved optimization results, real field plot and exports. The live server returns HTTP 200 at `http://localhost:8502`. Browser visual inspection could not run because local browser use is disabled in Work settings; no screenshots are claimed.

The initial 24-analysis pilot, a 120-analysis unstratified diagnostic expansion, and the corrected 120-analysis LHS experiment are stored separately. Only the last dataset trains the active model. Its held-out MLP test metrics are stress MAE 14.9736 MPa / RMSE 16.9187 MPa / R² 0.98623 and displacement MAE 0.00730383 mm / RMSE 0.00940232 mm / R² 0.99363. See ML_EVALUATION.md for all model comparisons and train/validation/test separation.

## Acceptance criteria
PASS below means evidence for the explicitly stated numerical scope, not full engineering qualification.

| # | Criterion | Status | Evidence / qualification |
|---|---|---|---|
| 1 | Original unchanged | PASS | Original HEAD and remote comparison; isolation-final.json |
| 2 | Separate fork/branch | PASS | Hiten41 fork and named feature branch |
| 3 | Consistent CAD/export/mesh | PASS | Single solid; real bores and section probes; STEP/STL volume checks |
| 4 | Correct tested mechanics | PASS | Independent rectangle inertia and axial calculations; instability rejection |
| 5 | Real CalculiX execution | PASS | 264 dataset analyses plus reference, refinement and optimization solves; simulation-inventory.csv |
| 6 | No silent fallback | PASS | Failure regression and preserved failed-run logs |
| 7 | Verified simulation data | PASS | 120 active batch-LHS records; separate provenance |
| 8 | Held-out surrogate evaluation | PASS | 72/24/24 grouped split; active model metadata and plots |
| 9 | Converged constrained optimizer | PASS | Three converged starts, independent checks at stated mesh; global optimum not claimed |
| 10 | Independent final CalculiX check | PASS | Final guarded candidate, both load cases at 1.75 mm |
| 11 | Running Streamlit interface | PASS | HTTP 200 and AppTest; visual browser review BLOCKED |
| 12 | Accurate displayed provenance | PASS | Explicit analytical/ML/FEA distinctions and mesh qualification warning |
| 13 | Matching final exports | PASS | Exact parameter equality, CAD mass and STL checks in final-export-check.json |
| 14 | Documentation and tests | PASS | Required reports, pytest, CI workflow and source architecture |

## Unfinished requirements and review recommendation
- **FAIL — provisional peak-stress convergence target:** stable displacement does not establish converged maximum stress. This prevents full engineering acceptance. Resolve sharp transitions and revalidate the governing stress measure before hardware use. The 20% search allowance is not a substitute.
- **BLOCKED — screenshots and browser visual QA:** local browser use is disabled. Functional UI checks passed; a person can open the local URL and review layout/interaction.
- **Not demonstrated — fresh meshing of a bundled FreeCAD FEM benchmark:** its provided deck was solved; the independent bar and actual rod were meshed and solved through the implemented path.
- **PASS — hosted CI:** [GitHub Actions run 42650420767](https://github.com/Hiten41/Automated-Connecting-Rod-Weight-Optimization/actions/runs/42650420767) passed on implementation commit `363e520e`. The hosted job runs ordinary Python tests; the real external-solver tests passed locally and are not claimed as hosted solver validation.

The isolated branch is ready for **technical review of the research implementation**. Do not merge or label it a fully validated mechanical design. Review peak-stress treatment and visually inspect the application before deciding whether to open a PR. The user will decide; no PR is opened by this work.