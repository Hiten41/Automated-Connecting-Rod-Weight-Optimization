# Windows reproduction

## Prerequisites

- Python 3.13 x64 for the application and Gmsh Python API.
- The bundled FreeCAD 1.1.4 Python runtime and CalculiX 2.22 executable for CAD/solver workers.
- PowerShell and Git.

The checked-in `requirements-validated.txt` records the tested Python package versions. The machine-specific `local_config.json` is intentionally ignored by Git.

## Environment setup

From the Phase 4 worktree root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-validated.txt
```

Create `local_config.json` with the installed paths for `freecad_python` and `ccx`:

```json
{
  "freecad_python": "C:\\Path\\To\\FreeCAD\\bin\\python.exe",
  "ccx": "C:\\Path\\To\\FreeCAD\\bin\\ccx.exe"
}
```

## Launch the application

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\streamlit.exe run app.py --server.port 8505
```

Open [http://localhost:8505](http://localhost:8505). Phase 2 and Phase 3 are separate worktrees on ports 8503 and 8504.

## Reproduce evidence

With `local_config.json` present, the CAD search and paired FEA scripts are:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe scripts/phase4_design_space.py --output runs/phase4-design-space-lhs --target-per-family 12 --max-attempts-per-family 24 --seed 20261111
.\.venv\Scripts\python.exe scripts/phase4_fea_screen.py --root runs/phase4-design-space-lhs --per-family 3 --mesh-mm 6
.\.venv\Scripts\python.exe scripts/phase4_refine_candidates.py --root runs/phase4-design-space-lhs --candidates P4-0065 --levels 0.75 0.5
.\.venv\Scripts\python.exe scripts/phase4_finalize_evidence.py
.\.venv\Scripts\python.exe scripts/build_phase4_dataset.py
.\.venv\Scripts\python.exe scripts/phase4_ml_evaluation.py
.\.venv\Scripts\python.exe scripts/phase4_figures.py
```

The exact finalized meshes and solver results are retained in `evidence/phase4/phase4-solver-evidence.zip`. The CLI commands above rerun CAD and FEA, so they require the configured local FreeCAD and CalculiX paths.
