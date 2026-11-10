# Phase 4 verification results

Verification was run on the isolated Phase 4 branch. The current source revision is recorded by the Git history and evidence manifests created after the final source commit.

## Python and CAD/FEA tests

- Complete suite: **119 passed, 0 failed, 0 skipped** (`pytest -q`). The JUnit report is `data/phase4/all-test-results.xml`.
- Integration marker: **9 passed, 110 deselected** (`pytest -m integration -q`). The JUnit report is `data/phase4/integration-test-results.xml`.
- Unit/non-integration marker: **110 passed, 9 deselected** (`pytest -m "not integration" -q`). The JUnit report is `data/phase4/unit-test-results.xml`.
- Integration coverage exercised the configured local FreeCAD, Gmsh and CalculiX paths, load scaling, design-family screening and background CAD-job exports. These checks validate the recorded software workflows; they are not independent solver verification of the connecting-rod model.
- `compileall`/module compilation: passed. `git diff --check`: passed.

## Ruff

- Modified Phase 4/UI/package Python scope: `ruff check` passed.
- Modified Phase 4/UI/package Python scope: `ruff format --check` passed.
- Repository-wide `ruff check . --statistics`: **225 findings**. These findings are outside the clean modified-file scope; the implementation does not claim a repository-wide zero-finding result.

## Playwright browser QA

- Playwright **1.65.0**, headless Microsoft Edge/Chromium **157.0.4341.46**.
- Ten routes checked at five viewport sizes: **50 route/viewport cases** across 390×844, 768×1024, 1024×768, 1440×1000 and 1920×1080.
- Dashboard, geometry editor and family selection, engine loading, simulation, optimization, results/structural analysis, ML analytics, design-space/topology exploration and reports were inspected. The geometry-family selector was changed and verified without starting CAD/FEA.
- Browser report: `outputs/phase4-visual-qa/browser-qa-report.json`; screenshots: `outputs/phase4-visual-qa/`.
- The browser checks verify page content, controls, collapsed diagnostics, visible JSON, raw internal-data tokens, horizontal overflow, mobile sidebar closure/occlusion, Streamlit exceptions, console/page errors, failed requests and HTTP errors. They do not establish engineering qualification.

## GitHub Actions

The GitHub Actions result and run URL are recorded after the Phase 4 branch push in `outputs/phase4-visual-qa/github-actions-status.json`. The workflow runs Ruff/format checks for the modified Phase 4 source and non-integration Python tests; CAD/FEA integration checks are run separately on the configured local workstation and are not represented as hosted CI coverage.

## Engineering status

The project records a finite set of candidate screening results. No independently solver-verified, fatigue-qualified, production-suitable or experimentally validated connecting rod is claimed. See `LIMITATIONS.md` and `FINAL_DESIGN_VALIDATION.md`.
