# Website QA

Local Phase 2 endpoint: http://localhost:8503 (bound to127.0.0.1, no public deployment).

Implemented: dashboard/readiness; all nine geometry controls and explicit CAD preview; manual/engine loading with CSV; sourced reference limitations and cycle plots; material/mesh/BC/load-case selection; background FEA/optimization; actual Gauss-point stress and nodal displacement/deformation; centroid-mean option; peak markers; side-by-side CAD; convergence charts and counts; grouped ML comparison/residuals/coverage; reports and CAD/CSV/JSON/input/log downloads.

Streamlit AppTest checks every section, all geometry fields and reference-engine plot calculation. HTTP `/_stcore/health` returned `ok`. These are functional checks, not browser visual inspection.

Browser QA attempted with the available browser tool. Exact blocker: **Local browser use is disabled in Work settings**. No desktop/narrow-viewport visual QA or screenshots are claimed. No screenshots were fabricated. Enable local browser use if visual inspection is desired; no setting was bypassed.

Stress visualization uses actual integration-point coordinates and unaveraged stresses, with deterministic display decimation if needed. It is a point cloud, not an invented smooth surface. Displacement points are displaced by the displayed magnification; colors remain actual nodal magnitude. Local peak scalar uses all data.

Final local suite:61 passed, including3 real external integration tests. Final ordinary test subset:58 passed,3 external tests deselected. Evidence: `evidence/phase2/local-tests.xml` and `final-unit-tests.xml`. The suite includes the final background CAD preview/export workflow.
