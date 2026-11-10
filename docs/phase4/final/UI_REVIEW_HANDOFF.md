# RodLab Phase 4 UI review handoff

## Review purpose and boundary

This handoff accompanies `outputs/phase4-complete-review-bundle/rodLab-phase4-complete-source.zip` and the five under-512 MB final solver-evidence ZIP parts. It is intended for independent review of the implementation and actual browser screenshots. It does not imply that another reviewer has already inspected the ZIPs. The work remains on `feature/phase4-physics-guided-redesign`, based on Phase 3 commit `0981e89f8189814041813b26d9dd4c2f1cd35ef1`; the exact final commit is recorded in both the source ZIP and solver-evidence manifests.

## Run the application on Windows

From the project root, create/activate the configured Python environment, install the project with its test extra, and launch:

```powershell
python -m pip install -e ".[test]"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m streamlit run app.py --server.port 8505
```

Open `http://localhost:8505`. CAD/FEA actions require separately installed and configured FreeCAD, Gmsh and CalculiX. Browser QA does not submit expensive FEA jobs.

## Page inventory and source

| Route | Entry module | Renderer |
|---|---|---|
| Dashboard | `pages/dashboard.py` | `src/conrod/ui/views/dashboard.py` |
| Design Studio | `pages/design_studio.py` | `src/conrod/ui/views/design_studio.py` |
| Design Space Explorer | `pages/design_space_explorer.py` | `src/conrod/ui/views/topology_explorer.py` |
| Legacy Geometry Editor | `pages/legacy_geometry_editor.py` | `src/conrod/ui/views/geometry_designer.py` |
| Engine Loading | `pages/engine_loading.py` | `src/conrod/ui/views/engine_loading.py` |
| Simulation | `pages/simulation.py` | `src/conrod/ui/views/simulation.py` |
| Results & Comparison | `pages/results_comparison.py` | `src/conrod/ui/views/results.py` |
| Model Analytics | `pages/model_analytics.py` | `src/conrod/ui/views/model_analytics.py` |
| Optimization & Feasibility | `pages/optimization_feasibility.py` | `src/conrod/ui/views/optimization.py` |
| Reports & Downloads | `pages/reports_downloads.py` | `src/conrod/ui/views/reports.py` |

`app.py` configures the theme, shared qualification note, session defaults and job status. `src/conrod/ui/navigation.py` defines grouped routes. `app_shell.py`, `state.py` and `data_access.py` manage job lifecycle, session state and project-backed data. The corresponding engineering modules in `src/conrod/` own calculations and schemas.

## Interactions and data flow

Geometry and loads are held in Streamlit session state. Expensive jobs only start after an explicit submit action. Inputs are snapshotted in `runs/ui-phase4/<job-id>/job.json`; the worker writes results/logs to that directory. Refresh reads the saved job path, allowing recovery after browser refresh. Results and model analytics consume stored Phase 4 evidence; ML never enforces structural constraints. Diagnostics remain in collapsed developer-only disclosures.

The actual figures include CAD previews, stored FEA fields, row-level prediction-versus-FEA and residual plots, and engineering candidate comparisons. Stress points retain their integration-point values; displacement uses nodal vectors and an explicit magnification. Browser screenshots are actual renders from the local application, not mockups.

## Responsive behavior and known limitations

Navigation is grouped into Overview, Design, Loads and Simulation, Analysis, and Project. On mobile the Streamlit hamburger opens the sidebar; clicking a route closes it so it no longer covers the main content. Metric grids use two columns at phone widths. Long technical tables and charts remain vertically scrollable. No automated screen-reader or full manual accessibility certification is claimed.

Engineering limitations are summarized in `LIMITATIONS.md`: no component-certified material condition, validated nonlinear pin contact, fatigue qualification, defensible continuum error bound, independent solver verification, manufacturing release, or required physical test is claimed. The parametric study is finite and not SIMP topology optimization.

## Screenshot index

The browser report at `outputs/phase4-visual-qa/browser-qa-report.json` lists each route/viewport result and corresponding screenshot paths. For every route it records a viewport and a full-page screenshot at each of 390×844, 768×1024, 1024×768, 1440×1000 and 1920×1080. Dashboard detail shots and the geometry-family interaction shot are included where the run completes those interactions. The folder also preserves the earlier dashboard before-fix capture for comparison.
