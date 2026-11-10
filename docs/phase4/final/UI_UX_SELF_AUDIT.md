# RodLab Phase 4 UI/UX self-audit

## Scope

The review covers Dashboard, Design Studio, Design Space Explorer, Legacy Geometry Editor, Engine Loading, Simulation, Results & Comparison, Model Analytics, Optimization & Feasibility, and Reports & Downloads. Browser inspection uses the running Streamlit application at `http://localhost:8505` with headless Playwright and Microsoft Edge.

## Implemented changes

- Grouped the ten routes using Streamlit-native page navigation and a mobile hamburger.
- Added automatic mobile sidebar closure after a route click and a regression check for sidebar occlusion.
- Added shared navy, teal, light-surface theme tokens, compact status/metric cards, wrapping labels, and a two-column mobile metric layout.
- Kept engineering status and research qualification visible without repeating the large warning banner on every route.
- Moved views into page modules and shared `src/conrod/ui/` modules; the entry point remains small.
- Kept raw JSON, job logs and internal diagnostics inside collapsed developer-only sections.
- Used Phase 4 prediction records for analytics and distinguished historical Phase 3/2 information.
- Used curated candidate labels and actual stored fields on Results & Comparison.

## Automated browser checks

The Playwright suite checks 10 routes at 390×844, 768×1024, 1024×768, 1440×1000 and 1920×1080. It records viewport/full-page screenshots, verifies route content and selected interactions, checks for visible raw JSON and Streamlit exceptions, measures horizontal overflow and heading bounds, tests mobile sidebar closure/occlusion, and collects console, page, HTTP and failed-request errors. The machine-readable results are in `outputs/phase4-visual-qa/browser-qa-report.json`; screenshots are in `outputs/phase4-visual-qa/`.

The final report records case counts and any remaining browser issues. A zero horizontal-overflow result does not by itself certify usability; the mobile sidebar geometry is checked separately. Browser inspection does not certify engineering results.

## Remaining UI limitations

- Streamlit's native widgets constrain fine-grained visual control and use vertical document flow.
- Some evidence tables and solver plots remain long on narrow screens; they reflow and may require scrolling.
- Automated accessibility testing does not replace a manual screen-reader, keyboard and contrast review.
- High-density field plots can be visually busy; plotted point decimation does not change stored peak values.
- CAD/FEA tool dependencies and their versions remain host-specific.
