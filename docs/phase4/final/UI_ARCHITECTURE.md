# RodLab Phase 4 UI architecture

## Application entry and routing

`app.py` is the Streamlit entry point. It configures the page theme, initializes session state, mounts the shared research status and job controls, and registers grouped `st.navigation` routes through `src/conrod/ui/navigation.py`. Thin modules under `pages/` dispatch to view functions under `src/conrod/ui/views/`. Reusable state, data loading and diagnostics are in `src/conrod/ui/state.py`, `data_access.py` and `app_shell.py`.

Navigation groups are Overview (Dashboard), Design (Design Studio, Design Space Explorer, Legacy Geometry Editor), Loads and Simulation (Engine Loading, Simulation), Analysis (Results & Comparison, Model Analytics, Optimization & Feasibility), and Project (Reports & Downloads). At mobile widths, the sidebar opens with Streamlit's hamburger; a small local event handler closes it after route selection.

## Page and data mapping

| Page | View module | Primary project data and interactions |
|---|---|---|
| Dashboard | `views/dashboard.py` | Stored Phase 4 assessments, search manifests, CAD masses, FEA fields, current editor geometry/load state; summary KPIs and plots |
| Design Studio | `views/design_studio.py` | `FamilyDesign`, material and mesh settings; explicit CAD/FEA submission only |
| Design Space Explorer | `views/topology_explorer.py` | Seeded and Latin-hypercube manifests, coarse FEA records, refined candidate evidence; finite parametric screening |
| Legacy Geometry Editor | `views/geometry_designer.py` | `Geometry` schema, session dimensions and explicit preview/job submission |
| Engine Loading | `views/engine_loading.py` | Engine reference parameters, pressure CSV or approximate digitized reference plot; cycle plots and load transfer |
| Simulation | `views/simulation.py` | Active geometry, material, mesh and load cases; explicit background FEA submission |
| Results & Comparison | `views/results.py` | Curated refined candidates and actual raw fields, CAD views, prior results, field/deformation controls and downloads |
| Model Analytics | `views/model_analytics.py` | `data/phase4/ml-evaluation.json` as primary, separated Phase 3/2 historical evaluations, actual stored prediction rows |
| Optimization & Feasibility | `views/optimization.py` | Finite candidate ranking, recorded screen statuses, constraint margins and outstanding verification gates |
| Reports & Downloads | `views/reports.py` | Final Markdown reports, generated exports and curated CAD/FEA/ML artifact library |

## Shared state and data flow

The session state holds active geometry/family, load cases and provenance, engine-cycle results, selected candidate, and the current background-job ID/path/process handle. Job inputs are frozen under `runs/ui-phase4/<job-id>/job.json`; `scripts/run_job.py` performs requested work and writes `ui-result.json` plus `background.log`. Status can be re-read from the saved directory after a refresh even when a Python `Popen` object is unavailable. Historical Phase 3 jobs remain readable.

Batch engineering evidence is file-backed under `data/phase4/`, `runs/phase4-*`, `models/` and `docs/phase4/final/`. Views consume the engineering modules and saved solver results; they do not implement separate stress, buckling or acceptance equations. FEA field plots use saved integration-point and nodal field records.

```text
app.py → grouped Streamlit navigation → page dispatcher → view module
                                               ├─ project JSON/CSV/JSONL → curated UI
                                               ├─ session state → editable study inputs
                                               └─ explicit job submit → frozen job → worker → saved results
```

## Theme, responsive behavior and disclosure

`src/conrod/ui/theme.py` holds the navy/teal/light-surface tokens, typography, compact metric cards and breakpoints. On narrow viewports four-up metric rows become two columns where space permits. Streamlit's native route links use its mobile hamburger, with a local click handler to collapse the mobile sidebar after selection. The research qualification note remains visible.

Raw diagnostic structures and worker logs appear inside collapsed **Advanced diagnostics — Developer only** disclosures. Normal views use labeled metrics, tables, charts, status text and download actions. Source records remain available for audit without changing the solver data.

## Visualization and engineering boundary

Dashboard and exploration plots are derived from stored records. Results & Comparison distinguishes actual unaveraged integration-point stress, nodal displacement with explicit magnification, and element-mean point clouds. CAD geometry is displayed from available exports. Linear buckling, numerical screens, mesh trends, exploratory predictions, independent verification and mechanical qualification remain separate labels.

Known limitations include Streamlit's vertical page flow, long tables/plots on mobile, no component-level automated accessibility audit, and local FreeCAD/Gmsh/CalculiX dependency configuration. The finite parametric search is not SIMP density topology optimization. No global optimum or mechanically qualified part is claimed.
