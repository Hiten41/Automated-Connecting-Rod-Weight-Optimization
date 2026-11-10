# Phase 4 website QA

## Dashboard raw-data root cause and fix

The raw dictionary came from three direct `st.json()` calls in the former Dashboard branch of `app.py`: the Phase 3 feasibility summary (`read(data)`), the mesh-convergence record (`read(conv)`) and the search-count dictionary (`study.get("counts", {})`). The feasibility summary call produced the visible `attempted_geometries` object. The current dashboard renderer is `src/conrod/ui/views/dashboard.py::render_dashboard`; it now turns stored source records into metrics, constraint tables, candidate comparisons and plots. Its raw source records remain available from a download inside the collapsed **Advanced diagnostics — Developer only** expander. The current dashboard has no raw JSON renderer in its normal presentation.

The application-wide raw-diagnostic helper, `src/conrod/ui/app_shell.py::render_advanced_diagnostics`, renders JSON only inside a collapsed developer expander. Raw solver logs are also inside that collapsed expander. Results-page diagnostic JSON remains opt-in and collapsed. Regular pages show curated values, plots and tables; the underlying engineering records remain intact.

## Browser method and results

- Running application: [http://localhost:8505](http://localhost:8505), verified by successful page loads (HTTP 200).
- Browser: Playwright 1.65.0 with Microsoft Edge/Chromium 157.0.4341.46, headless.
- Ten workspace routes were checked at five viewports: 390×844, 768×1024, 1024×768, 1440×1000 and 1920×1080 (50 route/viewport cases).
- Route checks cover Dashboard, Legacy Geometry Editor, Engine Loading, Simulation, Optimization & Feasibility, Results & Comparison, Model Analytics, Reports & Downloads, Design Studio and Design Space Explorer.
- Browser QA selects **Tapered I section** and verifies the selection without starting a CAD/FEA job. It checks the stored solver-field view, analytics plots, optimization ranking, design-space plots and report download controls.
- Assertions check visible JSON, raw internal-data tokens, horizontal overflow, heading clipping, mobile sidebar visibility/occlusion, Streamlit exceptions, browser console/page errors, failed network requests and HTTP status errors. The final machine report records the run's exact issue/case counts and digest.

These are UI interaction and rendering checks against the local research application; they do not validate the engineering model or replace the CAD/FEA test reports.

## Screenshots

The before image shows the historical raw summary JSON. The after images are from the current automated run; all page screenshots and the machine-readable report are under `outputs/phase4-visual-qa/`.

![Dashboard before correction: raw Phase 3 feasibility object](../../../outputs/phase4-visual-qa/before/dashboard-desktop.png)

![Dashboard after correction: mobile viewport](../../../outputs/phase4-visual-qa/dashboard-390x844-viewport.png)

![Dashboard after correction: desktop viewport](../../../outputs/phase4-visual-qa/dashboard-1440x1000-viewport.png)

![Dashboard actual engineering data visualizations](../../../outputs/phase4-visual-qa/dashboard-details-1440x1000.png)
