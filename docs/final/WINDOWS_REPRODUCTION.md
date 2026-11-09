# Windows reproduction

## Tested toolchain

The Phase 3 worktree was run with Python 3.13 for the application/tests, portable FreeCAD 1.1.4 with its bundled Python 3.11 worker, Gmsh 4.15.2 and CalculiX 2.22. Install the Python package and test dependencies into an application virtual environment. Set `CONROD_FREECAD_PYTHON` and `CONROD_CCX` to the portable FreeCAD interpreter and solver, or use an ignored local `local_config.json`. The project never commits machine-specific executable paths.

From PowerShell at the Phase 3 worktree root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[test]
$env:CONROD_FREECAD_PYTHON = 'C:/path/to/FreeCAD/bin/python.exe'
$env:CONROD_CCX = 'C:/path/to/FreeCAD/bin/ccx.exe'
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe scripts/check_environment.py
```

Each simulation run stores its request, CAD exports, mesh/provenance, CalculiX input deck, DAT/FRD/STA/log and raw field JSON when solved. The .25 mm baseline mesh demonstrates the node-budget guard and has no solver fields. Do not describe a rejected or failed run as solved evidence.

## Recreate the feasibility and paired dataset

The checked-in feasibility records retain the fixed seed 7301 design plan and its 40 attempted geometries. Re-running the solver-heavy stage is optional when the records are present:

```powershell
.\.venv\Scripts\python.exe scripts/phase3_feasibility.py --limit 40 --count 40
.\.venv\Scripts\python.exe scripts/phase3_feasibility_report.py
.\.venv\Scripts\python.exe scripts/phase3_refine_candidates.py --count 1
.\.venv\Scripts\python.exe scripts/phase3_paired_fidelity.py --groups 12 --limit 12
.\.venv\Scripts\python.exe scripts/train_surrogate.py --dataset data/phase3/paired/fine.jsonl --output models/phase3_surrogate.joblib
```

The paired study reuses 6 mm coarse records from the feasibility dataset and adds 1.25 mm and 0.75 mm compression/tension analyses for 12 selected geometries. It checkpoints each run and can be resumed. The resulting 0.75 mm fine labels are a specific dataset fidelity, not a general convergence guarantee. Allow the paired study to finish before starting another solver batch; the configured limits are 250,000 nodes and 600 seconds per solver case.

## Tests, application and evidence package

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8504
.\.venv\Scripts\python.exe scripts/package_evidence.py outputs/phase3-solver-evidence --critical-phase3-fields --zip
```

Open `http://localhost:8504`. Phase 2 can remain running on port 8503. The package command creates `outputs/phase3-solver-evidence.zip` with a manifest and raw critical fields. The Python integration tests require configured FreeCAD and CalculiX. Ordinary hosted CI exercises Python tests only and is not full FEA validation.
