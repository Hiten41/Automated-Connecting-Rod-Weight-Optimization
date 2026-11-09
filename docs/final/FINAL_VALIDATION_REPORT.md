# Phase 3 final validation report

## Result summary

Phase 3 adds reproducible engineering evidence to an isolated branch, but it does **not** establish a feasible lightweight connecting-rod design. The baseline is over the stated stress allowable, no candidate in the 40-geometry screen passed its coarse stress screen, and the closest sample fails tension after 0.75 mm refinement. The finite search is inconclusive about the rest of the supported design domain; no global infeasibility or optimum is claimed.

The strongest new structural evidence is a fixed-geometry, full-thickness 0.75/0.50/0.35 mm refinement sequence for the baseline. Both load cases meet a provisional two-step under-5% successive-change rule for peak unaveraged integration-point stress and displacement. The independently generated meshes are non-nested, the 0.25 mm model exceeds the 250,000-node budget, and no continuum error bound is reported. Curved pin contact likewise remains unqualified, so the rod results use the equivalent-pressure COSINE_BEARING model.

## Structural configuration and measured result

The baseline geometry has a FreeCAD volume-derived mass of 735.326854 g. The model uses isotropic linear 4340 steel with E = 205 GPa, ν = 0.29 and density = 7,850 kg/m³. Yield strength 710 MPa is an assumption pending a material certificate; with the required FoS of 1.8, the screening allowable is 394.444 MPa. The displacement limit is 0.35 mm. Loads are 28 kN compression and 18 kN tension, checked separately with balanced cosine-shaped bore pressure and six gauge degrees of freedom.

| Local target | Nodes / elements | Compression: max IP stress / displacement / FoS | Tension: max IP stress / displacement / FoS | Status |
|---:|---:|---:|---:|---|
| 0.75 mm | 96,863 / 62,626 | 519.417 MPa / 0.0989999 mm / 1.367 | 721.779 MPa / 0.1758622 mm / 0.984 | Both stress screens fail |
| 0.50 mm | 120,889 / 79,545 | 545.732 MPa / 0.0991032 mm / 1.301 | 740.474 MPa / 0.1759833 mm / 0.959 | Both stress screens fail |
| 0.35 mm | 179,366 / 121,674 | 566.718 MPa / 0.0990872 mm / 1.253 | 770.139 MPa / 0.1760778 mm / 0.922 | Both stress screens fail |

At 0.35 mm, displacement meets its limit but both stresses exceed the allowable. The governing hotspot is at the big-end/shank transition near a finite 1 mm CAD fillet, not at a gauge node. Fixed-region maxima show the same transition governs; the big-bore 2 mm band is the next largest reported region. See [mesh and hotspot evidence](MESH_CONVERGENCE.md) and [raw FEA results](FEA_RESULTS.md).

## Engine and contact validation

The Ricardo Hydra example combines published dimensions with approximate digitized force-plot readings. It checks slider-crank kinematics and force balance against published graph values, but it is not raw cylinder-pressure evidence or experimental combustion validation. No matching rod mass/center of gravity was found; optional two-end rod-mass allocation is an approximation. The design load requirements remain 28/18 kN and are not replaced by the lower literature example. Sources and limitations are in [engine validation](ENGINE_LOAD_VALIDATION.md).

Three flat frictionless contact patch tests agree with analytical reaction/compliance within 0.15%. A separate curved pin/ring benchmark balances reaction forces but peak pressure changes materially with mesh and penalty stiffness. It does not qualify contact for the connecting rod. The primary structural boundary model remains COSINE_BEARING, explicitly an equivalent bearing-pressure approximation; see [boundary conditions](BOUNDARY_CONDITIONS.md).

## Feasibility, learning and optimization

The seeded Latin-hypercube search attempted 40 geometries: 35 passed CAD validation and completed 6 mm compression/tension FEA, while five failed geometry validation. Zero valid samples passed the coarse stress screen. The nearest candidate has mass 690.247 g and coarse stress 323.140/409.298 MPa; its 0.75 mm results are 374.866/501.358 MPa, so it fails tension FoS at 1.416. Its nominal 6.1% mass difference is not an accepted reduction. The study does not prove the full domain infeasible; see [feasibility results](FEASIBILITY_STUDY.md).

Phase 3 has 72 paired labels across 12 geometries: 24 existing 6 mm coarse analyses plus 24 new 1.25 mm intermediate and 24 new 0.75 mm fine analyses. The fine model's geometry-grouped split is 6/3/3 training/validation/test geometries. Validation-selected MLP test stress MAE is 208.86 MPa, RMSE 291.95 MPa and R² 0.031; the two near-constraint test analyses have 56.29 MPa stress MAE and negative R². The model is exploratory only, and the optimizer is deliberately guarded. No constrained search, independent candidate verification or optimized mass reduction is claimed; see [dataset provenance](DATASET_PROVENANCE.md), [ML evaluation](ML_EVALUATION.md) and [optimization results](OPTIMIZATION_RESULTS.md).

## Software, tests and reproducibility

The parametric FreeCAD → Gmsh → CalculiX workflow, frozen job records, local evidence views and Streamlit application remain on the isolated Phase 3 branch. The Phase 3 and preserved Phase 2 local health endpoints are checked separately; application results remain research outputs, not a hardware certificate. Visual browser inspection was blocked because browser access is disabled by the current Codex Work setting, so no screenshots or responsive-layout inspection are claimed.

The final test report, GitHub Actions run, and packaged raw field evidence are recorded with the completed release checkpoint. Reproduction steps and exact tool requirements are in [Windows reproduction](WINDOWS_REPRODUCTION.md). Historical Phase 1's reported 47.668% mass reduction remains tied to its sharp-pocket geometry and clamped-bore model and is not carried forward as a Phase 3 result. The comparison is in [Phase 1/2/3 experiments](PHASE1_PHASE2_PHASE3.md).

## Acceptance status

| Requirement | Status | Evidence / remaining limit |
|---|---|---|
| Parametric CAD, valid topology and mass | Demonstrated | FreeCAD generation, geometry tests and volume-derived CAD mass; see geometry report |
| Engine load calculations | Demonstrated with limitations | Kinematics and force balance; digitized literature readings, not raw pressure validation |
| Justified boundary conditions | Incomplete | COSINE_BEARING balances loads; curved pin contact remains mesh/penalty sensitive |
| Actual CalculiX execution and field integrity | Demonstrated | Raw DAT/FRD/mesh/field artifacts retained for critical cases |
| Mesh validation | Limited | Baseline-specific provisional 5% successive changes; nonnested meshes and 0.25 mm budget stop |
| Geometry-diverse fine-mesh dataset | Exploratory | 12 selected geometries; paired labels do not establish converged truth |
| High-fidelity surrogate generalization | Incomplete | Small grouped holdout; screening only |
| Feasible design space | Inconclusive | No candidate in 40 samples; finite sampling cannot prove global infeasibility |
| Feasible optimized candidate and independent verification | Not achieved | No candidate passes stated constraints; objective remains unmet |
| Streamlit operation | Demonstrated locally | Port 8504 health check; visual browser QA blocked |
| Tests and CI | See final execution results below | Local suite and GitHub Actions are run on the completed commit |

## Software test results

The full local test suite completed with **70 passed**, including all three marked integration tests, in 49.08 seconds. The selected Ruff check (`--select E9,F`) passed for `app.py`, `src`, `scripts`, `tests` and `workers`. Streamlit health returned HTTP 200 on Phase 3 port 8504 and preserved Phase 2 port 8503. Browser screenshot/responsive inspection remains blocked by the Codex Work setting. The final fork push triggers the repository's Python 3.11 GitHub Actions unit-test workflow; its exact run status is recorded in the delivery response.

**Overall status: reproducible Phase 3 research implementation complete; engineering optimization incomplete.** No pull request, merge, or public deployment is made. Phase 1, Phase 2 and upstream main remain unchanged.
