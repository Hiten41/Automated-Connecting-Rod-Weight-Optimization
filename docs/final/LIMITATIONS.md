# Limitations and interpretation

## Structural model

No hardware qualification is claimed. The 710 MPa yield strength and 1.8 factor of safety are design assumptions pending a material certificate; the resulting allowable is 394.444 MPa. The solver model is static linear elasticity. It excludes plastic redistribution, fatigue, thermal loading, bolt preload, clearance dynamics, bearing-shell compliance, and a full distributed connecting-rod dynamic solution.

The production bearing load uses COSINE_BEARING, an equivalent pressure distribution. Flat frictionless patch tests verify force and compliance for a closed planar interface. The separate curved pin/ring contact benchmark is highly sensitive to mesh and penalty stiffness, so it has not qualified a nonlinear contact model for the rod. The baseline mesh sequence supports only a limited, geometry- and load-specific successive-change screen. Its meshes are independently generated and non-nested; this evidence does not establish a continuum error bound, validate all local stress measures, or generalize to other geometries.

Peak stress is the unsmoothed maximum von Mises stress at a CalculiX integration point. Hotspot coordinates and components are retained, and fixed physical regions were used for cross-mesh comparisons. The hotspot lies near a finite-radius CAD fillet and its sampled position changes with load and mesh. This does not establish a mathematical singularity or prove complete convergence. The 0.25 mm model was rejected by the node budget before solver execution.

## Engine and material data

The Ricardo Hydra example combines published engine geometry with approximate digitized readings from a published graph. The plot readings are not raw measured cylinder-pressure data, and calculated force values are not experimentally validated combustion loading. Matching connecting-rod mass and center of gravity were unavailable; the optional two-end rod inertia allocation is an approximation. The reference example is not asserted to define the 28 kN / 18 kN structural design envelope.

## Feasibility, ML and optimization

The 40-point sample is a finite, seeded exploration, not a proof that the supported domain is infeasible. Five attempted CAD geometries were invalid; none of the 35 valid coarse-FEA geometries passed the stress screen. The nearest coarse sample was refined once at 0.75 mm and still failed tension. No accepted weight reduction or global optimum is established.

Phase 2's surrogate labels are 8 mm mesh results and cannot certify fine-mesh stress. Phase 3 training uses a small geometry-grouped set and can support exploratory ranking only. Even a promising prediction requires actual CAD, FEA in both load directions, mesh review and independent verification. A small grouped test set cannot establish broad generalization or reliable out-of-distribution behavior.

## Application and evidence

Both local Streamlit health endpoints respond successfully. Browser screenshot capture and narrow-screen inspection are blocked by the current Codex Work setting, so visual browser QA remains incomplete. The evidence package carries raw critical solver artifacts and their provenance; generated visual point clouds are display-decimated, while reported extrema come from full integration-point results.

The original lightweight optimization objective remains unmet unless a new candidate independently satisfies all stated requirements under the selected model.
