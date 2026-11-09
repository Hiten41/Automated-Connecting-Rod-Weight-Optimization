# AI-driven connecting-rod optimization

Authors: Bhagavat Pratim Das (24JE0493) and Hiten Arora (24JE0503).

This isolated research implementation connects **FreeCAD CAD → Gmsh → CalculiX → verified simulation data → ML surrogate → constrained optimization → independent FEA verification**. It addresses all four proposal objectives without labelling analytical formulas as FEA.

**Research prototype, not hardware certification.** The solid has sharp transitions and uses an academic clamped-bore/distributed-traction model. Read the mesh convergence results before interpreting yield safety. No fatigue, bearing contact, dynamic engine-cycle or nonlinear buckling claims are made.

## Windows installation

1. Install Python 3.10+ and a portable [FreeCAD 1.1.4](https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4). The tested distribution includes `bin/python.exe` and `bin/ccx.exe`.
2. Open PowerShell in this repository on the feature branch:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CONROD_FREECAD_PYTHON = 'C:\path\to\FreeCAD\bin\python.exe'
$env:CONROD_CCX = 'C:\path\to\FreeCAD\bin\ccx.exe'
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Open <http://localhost:8502>. These executable paths are examples; select your actual portable installation. Alternatively use an untracked `local_config.json` with keys `freecad_python` and `ccx`. Do not point FreeCAD imports at system Python: the tested FreeCAD runtime uses Python 3.11, separately from the application.

## Reproducible workflow

```powershell
.\.venv\Scripts\python.exe scripts/validate_fea.py
.\.venv\Scripts\python.exe scripts/validate_fea.py --refine --output runs/refinement-baseline
.\.venv\Scripts\python.exe scripts/generate_fea_dataset.py --geometries 12 --output data/verified/pilot
.\.venv\Scripts\python.exe scripts/generate_fea_dataset.py --geometries 60 --seed 44 --output data/verified/expanded_lhs
.\.venv\Scripts\python.exe scripts/train_surrogate.py --dataset data/verified/expanded_lhs/verified.jsonl
.\.venv\Scripts\python.exe scripts/run_optimization.py --starts 3
.\.venv\Scripts\python.exe -m pytest -q
```

The default experiment fixes 145 mm center distance, 50/24 mm bores, steel, 28 kN compression, 18 kN tension, FoS ≥1.8, displacement ≤0.35 mm, Euler screening margin ≥1.8. Five geometry variables are optimized. The default dataset varies those variables, material and load with seeded LHS; `--vary-packaging` broadens the packaging domain. Do not claim generalization to packaging dimensions absent from training. The app rejects unsupported surrogate inputs.

The initial pilot must pass before expansion. The active experiment is `expanded_lhs` (seed 44); the earlier unstratified diagnostic run is retained separately and does not train the active model. Each geometry produces two analyses. Records contain the actual mesh, solver version, field locations, status and provenance; failures are reported separately. Re-running the same generation command resumes successful cases. Raw per-case CAD and solver artifacts stay in `data/verified/*/cases` locally; compact records and selected evidence are versioned. Archived legacy data is excluded from training.

Training compares Ridge, Extra Trees and a modest MLP. Geometry-grouped 60/20/20 splits keep related cases together. Model selection uses validation error; final comparison uses the held-out test set. Residual margins use observed validation underprediction, not calibrated confidence intervals. Only load trusted local joblib artifacts.

Optimization uses actual CAD mass, scaled multistart SLSQP, unrounded prediction values, independent constraint checks and bounded solver verification. A documented 1.2 stress guard multiplies prediction plus residual margin following the mesh-sensitivity study; this is a heuristic, not a certified error bound. The final reference is `runs/optimization-guarded`, verified at 1.75 mm. A failed or infeasible result remains a failure. No source branch/main modifications or upstream pull requests are part of this work.

## Application

Submit a form to run analytical estimates, CAD-only export, actual FEA or optimization. Long work runs in a subprocess; Refresh status reads completion. Geometry is neutral CAD. Actual solver samples, if shown, are labelled as element averages. JSON, CSV, STEP, STL, FCStd and solver fields refer to the exact displayed design.

Browser screenshot capture is blocked because local browser use is disabled in the desktop app settings. The HTTP health check and Streamlit AppTest are recorded; open the local URL to visually review. No screenshot is fabricated.

## Technical documentation

- [Architecture and module boundaries](docs/ARCHITECTURE.md)
- [Original defect audit](docs/TECHNICAL_AUDIT.md)
- [Engineering equations and assumptions](docs/ENGINEERING_ASSUMPTIONS.md)
- [FEA verification and refinement](docs/FEA_VALIDATION.md)
- [ML evaluation](docs/ML_EVALUATION.md)
- [Acceptance criteria and test evidence](docs/VALIDATION_REPORT.md)

Stack: Python, FreeCAD/OpenCASCADE, Gmsh, CalculiX, NumPy/SciPy, scikit-learn, Streamlit, Plotly, pytest. Ordinary Python tests run in CI. Solver integration tests are explicit and skipped only when dependencies are absent; skipped tests are never counted as solver validation.
