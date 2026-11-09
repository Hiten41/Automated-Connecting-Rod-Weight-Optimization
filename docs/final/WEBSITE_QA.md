# Website QA

The Phase 3 Streamlit application is running on `http://localhost:8504`, bound to `127.0.0.1`; its health endpoint returned HTTP 200 with `ok`. The preserved Phase 2 instance on port 8503 returned the same health response. No public deployment was made.

The existing Dashboard, Geometry Designer, Engine Loading, Simulation, AI Optimization, Results & Comparison, Model Analytics, and Reports & Downloads sections remain. Phase 3 adds explicit refinement configuration, separate Phase 3 model/dataset paths, feasibility and convergence evidence, optional rod-mass/CG inputs, and actual solver-field display. Application code only launches computational work after explicit submission and records frozen job inputs.

Actual solver-field visualizations are available as interactive local HTML in `evidence/phase3/`: unaveraged integration-point von Mises and nodal displacement point clouds for the 0.35 mm baseline cases, a mesh/hotspot region view, convergence plots, and feasibility-screen scatter plots. These are analytical outputs generated from actual solver fields; they are not screenshots of the running app.

The Model Analytics section reads the Phase 3 held-out model report. Its AI Optimization submission is disabled while the model is marked `EXPLORATORY_SCREENING_ONLY`; direct FEA remains available. Optimizer code independently rejects a screening-only Phase 3 model, so the app cannot accidentally present a small, poorly generalizing surrogate as a search basis.

**Visual browser QA is blocked.** The available browser tooling returned `Local browser use is disabled in Work settings`; no dashboard, narrow-screen, or section screenshots were captured. The full local suite passed 70/70 tests, including the three marked integration tests. Automated Streamlit AppTest does not replace visual browser inspection. No simulated screenshot is used as evidence.
