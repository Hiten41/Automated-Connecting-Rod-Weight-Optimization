# Phase 3 execution checkpoint

## Isolation and scope

All new work is on `feature/phase3-converged-feasible-design`, created directly from Phase 2 commit `5e480349ba11255f6fc44e709788c542d203a096`. The Phase 1, Phase 2 and upstream `main` branches are inputs only. No merge, pull request or public deployment is performed.

## Engineering evidence completed

- Historical Phase 2 raw fields were found; all eight focused-refinement peaks and displacements were reproduced from original DAT data. No historical solver cases were rerun.
- New fixed-CAD baseline runs at 0.75, 0.50 and 0.35 mm local transition target completed for both loads. Successive peak-stress changes meet the provisional <5% two-step screen; the independently regenerated unstructured meshes are nonnested, so no Richardson/GCI or continuum error bound is claimed. The 0.25 mm mesh exceeded the 250,000-node cap before solver execution.
- Actual integration-point global and fixed-region hotspot records include coordinates, components, element/IP IDs, CAD BREP face/radius distances, local edge sizes and element quality. Interactive HTML views use actual retained fields and state their display decimation/deformation scale.
- Three flat frictionless contact patch cases agree with analytical force/compliance within 0.15%. The separate curved pin/ring benchmark balances reactions but remains sensitive to mesh and penalty stiffness; it is not qualified for rod integration. The rod keeps COSINE_BEARING as an equivalent-pressure approximation.
- The Ricardo Hydra reference calculation preserves source and digitized-plot limitations. It is not raw cylinder-pressure evidence or experimentally validated combustion loading and does not replace 28 kN compression / 18 kN tension design requirements.
- The 40-point feasibility study evaluated 35 valid CAD geometries with both 6 mm load cases; five were invalid and no valid sample passed the stress screen. The nearest candidate was refined at 0.75 mm for both loads and fails tension.
- Paired Phase 3 data are complete: 12 geometries × 2 loads at 6 mm coarse, 1.25 mm intermediate and 0.75 mm fine. The 24 coarse records are reused from feasibility; all 48 new intermediate/fine solver runs succeeded. JSONL data and fidelity/source hashes are in `data/phase3/paired/manifest.json`.
- The grouped fine-mesh ML comparison is complete. Its validation-selected MLP has 208.86 MPa held-out stress MAE, 291.95 MPa RMSE, and R² 0.031 on three test geometry groups; near-constraint performance is also weak. The model is marked `EXPLORATORY_SCREENING_ONLY`. The optimizer API and UI reject this model, and no optimizer run or candidate acceptance is claimed.
- Phase 3 app health is HTTP 200 on port 8504; Phase 2 remains HTTP 200 on port 8503. Visual browser capture is blocked by the Codex Work setting and is not claimed.

## Validation and release checkpoint

- Current full local suite: **70 passed**, including all three FreeCAD/CalculiX integration tests, in 49.08 seconds.
- Ruff critical-error/undefined-name check (`--select E9,F`) on app, source, scripts, tests and workers: passed.
- Phase 3 and preserved Phase 2 Streamlit health endpoints: HTTP 200 `ok` on ports 8504 and 8503 respectively.
- Browser screenshot and narrow-screen inspection remain blocked by the Codex Work setting; no visual browser QA is claimed.
- The Phase 3 change set was committed on the isolated branch and pushed only to the verified fork ref. Phase 1, Phase 2, upstream `main`, and fork `main` retain their original hashes.
- GitHub Actions workflow `Python tests` passed on implementation commit `23cffba5d42f3d4929d698cba99eef0eef313b5b`, run `42718606232`. A documentation-only release checkpoint follows; its push is checked before delivery.
- The critical raw solver evidence is packaged under `outputs/phase3-solver-evidence.zip`. Its manifest records the source commit and per-artifact hashes; final archive integrity and critical-file inclusion are verified before delivery.
- No merge, pull request, public deployment, or hardware qualification is claimed.

## Reproducibility references

- Gmsh 4.15.2 documentation: https://gmsh.info/doc/texinfo/
- CalculiX 2.22 user manual, contact pair and surface behavior: https://www.dhondt.de/ccx_2.22.pdf
- AISI 4340 heat-treatment dependence: https://atlassteels.com.au/wp-content/uploads/2021/09/Through-Hardening-Low-Alloy-Steel-Bar-4340-Grade-Data-Sheet-10-09-21-1.pdf
