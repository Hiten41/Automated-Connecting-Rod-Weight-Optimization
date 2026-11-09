# AI-driven connecting-rod optimization — Phase 3

Authors: Bhagavat Pratim Das (24JE0493) and Hiten Arora (24JE0503).

FreeCAD → Gmsh quadratic tetrahedra → actual CalculiX fields → versioned FEA data → grouped surrogate evaluation → CAD-mass optimization → independent FEA.

**Research prototype, not mechanically qualified hardware.** Phase 3 continues the filleted geometry and cosine-bearing approximation with raw hotspot reconstruction, deterministic meshing, full-thickness local refinement, controlled pin-contact benchmarks and systematic design-space search. Engineering completion remains conditional on final feasibility evidence. The literature engine example remains approximate and does not establish experimentally validated combustion loading.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[test]
$env:CONROD_FREECAD_PYTHON = 'C:\path\to\FreeCAD\bin\python.exe'
$env:CONROD_CCX = 'C:\path\to\FreeCAD\bin\ccx.exe'
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8504
```

Open [localhost:8504](http://localhost:8504). The tested portable FreeCAD 1.1.4 includes Python 3.11 and CalculiX 2.22. Application Python is separate. An untracked local_config.json may provide freecad_python and ccx paths instead of environment variables. No private executable paths are committed.

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

See the [Phase 3 validation report](docs/final/FINAL_VALIDATION_REPORT.md), [engine loading](docs/final/ENGINE_LOAD_VALIDATION.md), [boundary/contact evidence](docs/final/BOUNDARY_CONDITIONS.md), [mesh convergence](docs/final/MESH_CONVERGENCE.md), [ML evaluation](docs/final/ML_EVALUATION.md), [website QA](docs/final/WEBSITE_QA.md), and [phase comparison](docs/final/PHASE1_PHASE2_PHASE3.md).

Phase 1 branch `feature/validated-rod-optimization` at1f5b5c44 remains preserved. Its734.577→384.418g result is historical, sharp-pocket/clamped-bore/manual-load and mesh-dependent. It is not reused as a Phase 3 result. Phase2 branch `feature/phase2-engine-loads-mesh-ui` at `5e480349` remains preserved; new work is on `feature/phase3-converged-feasible-design` in the Hiten41 fork. Upstream remains untouched.


## Phase 3 reproduction

The isolated Phase 3 branch is `feature/phase3-converged-feasible-design`, based on Phase2 commit `5e480349ba11255f6fc44e709788c542d203a096`. Use the separate phase3 worktree. Keep FreeCAD bundled Python for CAD workers and application Python for the package; set `PYTHONPATH` to this worktree's `src` when using the already prepared runtime.

```powershell
python scripts/phase3_field_audit.py
& 'C:/path/to/FreeCAD/bin/python.exe' workers/hotspot_features.py
python scripts/phase3_mesh_pilot.py
python scripts/phase3_refinement.py
python scripts/phase3_summarize_refinement.py
python scripts/phase3_contact_benchmark.py
python scripts/phase3_pin_benchmark.py
python scripts/phase3_contact_report.py
python scripts/phase3_feasibility.py --limit 40 --count 40
python scripts/phase3_feasibility_report.py
python scripts/phase3_refine_candidates.py --count 1
python scripts/phase3_paired_fidelity.py --groups 12 --limit 12
python scripts/train_surrogate.py --dataset data/phase3/paired/fine.jsonl --output models/phase3_surrogate.joblib
# Phase 3 optimization is guarded and currently unavailable: the 12-group model
# is marked EXPLORATORY_SCREENING_ONLY until held-out evidence supports use.
python scripts/phase3_visuals.py
& 'C:/path/to/FreeCAD/bin/python.exe' workers/phase3_hotspot_features.py
python scripts/phase3_hotspot_quality.py
python -m pytest -q
python scripts/package_evidence.py outputs/phase3-solver-evidence --critical-phase3-fields --zip
```

Each script checkpoints outputs. Solver limits are250000 nodes and600seconds; failed and over-budget cases are kept. Run feasibility sampling before candidate refinement and paired-fidelity generation. The latter are expensive; allow them to finish before launching another solver batch. Read `docs/final/EXECUTION_CHECKPOINT.md` and `FINAL_VALIDATION_REPORT.md` for measured status. The Phase3 GUI launch command uses port8504; Phase2 on8503 may remain running independently.

The current Phase3 model is marked `EXPLORATORY_SCREENING_ONLY`; both the optimizer API and UI reject it for optimization until held-out fine-mesh evidence supports that use. A successful application run would still require actual FEA and geometry-specific convergence review.
