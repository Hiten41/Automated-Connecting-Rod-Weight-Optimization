# AI-driven connecting-rod optimization — Phase 2

Authors: Bhagavat Pratim Das (24JE0493) and Hiten Arora (24JE0503).

FreeCAD → Gmsh quadratic tetrahedra → actual CalculiX fields → versioned FEA data → grouped surrogate evaluation → CAD-mass optimization → independent FEA.

**Research prototype, not mechanically qualified hardware.** Phase 2 adds fillets, compressive bearing-pressure loading, exact engine kinematics and a substantially expanded Streamlit workspace. Peak stress must be assessed with the recorded convergence evidence. The literature engine example is approximate and does not establish experimentally validated combustion loading.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[test]
$env:CONROD_FREECAD_PYTHON = 'C:\path\to\FreeCAD\bin\python.exe'
$env:CONROD_CCX = 'C:\path\to\FreeCAD\bin\ccx.exe'
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Open [localhost:8503](http://localhost:8503). The tested portable FreeCAD 1.1.4 includes Python 3.11 and CalculiX 2.22. Application Python is separate. An untracked local_config.json may provide freecad_python and ccx paths instead of environment variables. No private executable paths are committed.

## Reproduce

```powershell
python scripts/reference_engine.py
python scripts/fillet_feasibility.py
python scripts/phase2_experiments.py
python scripts/focused_refinement.py
python scripts/phase2_learning.py
python scripts/multifidelity.py
python scripts/engine_fea_example.py
python -m pytest -q
python scripts/package_evidence.py evidence --fields --zip
```

External integration tests require configured FreeCAD/CalculiX. Ordinary hosted Python CI is not full FEA validation. Simulations can take substantial time and retain large field files. Failed/over-budget runs are explicit, never replaced with analytical labels.

See [validation report](docs/VALIDATION_REPORT.md), [engine sources and limitations](docs/ENGINE_LOAD_MODEL.md), [bearing derivation](docs/BOUNDARY_CONDITION_COMPARISON.md), [mesh convergence](docs/MESH_CONVERGENCE.md), [ML evaluation](docs/ML_EVALUATION.md), [website QA](docs/WEBSITE_QA.md) and [historical comparison](docs/PHASE1_VS_PHASE2.md).

Phase 1 branch `feature/validated-rod-optimization` at1f5b5c44 remains preserved. Its734.577→384.418g result is historical, sharp-pocket/clamped-bore/manual-load and mesh-dependent. It is not reused as a Phase 2 result. All new work is on `feature/phase2-engine-loads-mesh-ui` in the Hiten41 fork; upstream remains untouched.
