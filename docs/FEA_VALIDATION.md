# FEA validation

## Toolchain and executed checks
FreeCAD 1.1.4 (portable, SHA256-verified distribution), bundled Python 3.11.14, CalculiX 2.22, Gmsh Python API 4.15.2. The application interpreter is Python 3.13.4. Runtime preflight passes FreeCAD/FEM imports, executable availability and output write permission. `-v` on this CalculiX build returns code 201 while emitting a valid version string; only that version query is specially handled. Analysis commands still require exit code zero, a completion marker and valid complete fields.

The bundled FreeCAD `ccx_cantilever_faceload.inp` solved with 228 displacement nodes and 316 integration-point stress records. This is a reference-deck smoke check, not a claim of independently calibrated beam accuracy. A separately meshed 100×10×10 mm axial bar with E=200000 MPa, ν=0 and F=1000 N gives analytical stress 10 MPa and extension 0.005 mm; CalculiX matched these within the recorded numerical tolerance. See `evidence/axial-patch.json`.

The rod uses one valid FreeCAD solid, STEP import, quadratic curved tetrahedra, geometric bore identification, full big-bore translation restraint and normalized distributed axial traction at the small bore. The INP force resultant is recorded and checked. See ENGINEERING_ASSUMPTIONS.md for the limitations of this boundary model.

## Refinement evidence
Each row is an actual independent mesh and solve. Small differences between repeated meshes reflect parallel meshing. Peaks are unaveraged integration-point values, not filtered to manufacture convergence.

| Design | Case | Size (mm) | Nodes / elements | Peak VM (MPa) | Max displacement (mm) | Runtime (s) |
|---|---|---|---|---|---|---|
| baseline | compression | 6.0 | 6423 / 3211 | 199.1515 | 0.0599555 | 2.56 |
| baseline | compression | 4.0 | 17153 / 9387 | 225.5973 | 0.0606527 | 5.63 |
| baseline | compression | 2.5 | 53417 / 32186 | 241.8709 | 0.0611967 | 25.85 |
| baseline | compression | 1.75 | 134145 / 85723 | 266.0057 | 0.0613560 | 129.19 |
| baseline | tension | 6.0 | 6445 / 3221 | 128.1162 | 0.0385417 | 2.32 |
| baseline | tension | 4.0 | 17155 / 9387 | 145.0314 | 0.0389882 | 5.36 |
| baseline | tension | 2.5 | 53356 / 32132 | 156.8960 | 0.0393490 | 25.22 |
| baseline | tension | 1.75 | 134645 / 86145 | 170.9925 | 0.0394501 | 124.23 |
| guarded_candidate | compression | 6.0 | 5758 / 2748 | 278.6224 | 0.1156431 | 2.86 |
| guarded_candidate | compression | 4.0 | 11345 / 5685 | 285.2765 | 0.1163031 | 3.65 |
| guarded_candidate | compression | 2.5 | 33292 / 18123 | 316.8516 | 0.1170439 | 10.74 |
| guarded_candidate | compression | 1.75 | 83466 / 49003 | 352.9309 | 0.1172791 | 35.67 |
| guarded_candidate | tension | 6.0 | 5741 / 2736 | 178.9676 | 0.0743191 | 2.38 |
| guarded_candidate | tension | 4.0 | 11343 / 5683 | 183.3946 | 0.0747657 | 3.58 |
| guarded_candidate | tension | 2.5 | 33199 / 18051 | 206.3311 | 0.0752338 | 10.43 |
| guarded_candidate | tension | 1.75 | 83565 / 49104 | 226.9738 | 0.0753936 | 36.45 |

## Convergence assessment
Displacements are relatively stable, but maximum stresses do **not** meet the provisional 5% refinement target consistently. The baseline hotspot centroids lie near the small-end/shank intersection (x≈130 mm, |y|≈12 mm), as recorded in `baseline-hotspots.json`. That sharp transition is a plausible singularity/concentration source; this location evidence does not prove mathematical singularity. Fillet/transition redesign, a defensible non-singular stress extraction rule and further refinement remain necessary before mechanical release.

A first 305.08 g candidate passed at 2.5 mm but its compression FoS fell to 1.8098 on a 1.75 mm mesh. It was superseded. The final search applies an explicit **1.2 multiplier to the predicted stress plus validation residual margin**, motivated by the observed mesh sensitivity. This is a conservative heuristic, not a calibrated statistical or discretization-error bound. It does not remove the convergence limitation.

The final guarded design mass is 384.418 g, versus 734.577 g for the same-load baseline (47.668% reduction). All requested yield/displacement/Euler screen constraints pass on the specified 1.75 mm meshes. It is a **provisional numerical candidate**, not a mesh-independent certified safe optimum.

## Failures and diagnostic integrity
Three initial handoff-debug runs failed with nonpositive Jacobians. They remain in `evidence/first-rod*-result.json` and corresponding solver logs. The root cause was overlong scientific numeric fields near zero, fixed by bounded coordinate formatting. No failed solve was converted to analytical success or admitted to the verified training dataset. Later pilot, unstratified diagnostic expansion and corrected batch-LHS expansion each completed without dataset solver failures.

The direct pipeline remeshes the rod from FreeCAD STEP. The bundled FreeCAD benchmark uses its shipped mesh; a fresh FreeCAD GUI FEM benchmark meshing workflow was not exercised. Solver paths and model assumptions are recorded for reproducibility.