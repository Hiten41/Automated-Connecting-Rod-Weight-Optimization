# Mesh convergence and hotspot evidence

## Fixed setup and criterion

The refinement sequence uses the same baseline CAD, assumed 4340 elastic material, 28 kN compression / 18 kN tension, and cosine-bearing boundary condition. The global target is 4 mm with a full-thickness local refinement field at the big-end/shank transition. Meshes are independently generated, single-threaded with fixed Gmsh 4.15.2 settings and seed 42; they are nonnested. Historical Phase 2 endpoint-centered balls and the Phase 3 full-thickness local boxes are different refinements and are not treated as one sequence.

The provisional convergence criterion is less than 5% change in both maximum unaveraged integration-point von Mises stress and maximum nodal displacement over two successive refinements. The 0.75 → 0.50 → 0.35 mm sequence meets that criterion for this baseline and these load/support definitions. This is a limited successive-change result, not a quantified continuum error bound. The 0.25 mm mesh generated 319,295 nodes, exceeded the 250,000-node cap, and was not solved.

| Local target (mm) | Load | Nodes | Elements | Peak stress (MPa) | Max U (mm) | FoS on 710 MPa assumption | Runtime (s) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0.75 | Compression | 96,863 | 62,626 | 519.417090 | 0.098999927 | 1.366917 | 142.98 |
| 0.75 | Tension | 96,863 | 62,626 | 721.779413 | 0.175862190 | 0.983680 | 120.86 |
| 0.50 | Compression | 120,889 | 79,545 | 545.732397 | 0.099103222 | 1.301004 | 141.28 |
| 0.50 | Tension | 120,889 | 79,545 | 740.474216 | 0.175983282 | 0.958845 | 159.62 |
| 0.35 | Compression | 179,366 | 121,674 | 566.717627 | 0.099087160 | 1.252829 | 346.84 |
| 0.35 | Tension | 179,366 | 121,674 | 770.138596 | 0.176077782 | 0.921912 | 307.15 |

Peak stress changes by 4.82% then 3.70% in compression and 2.52% then 3.85% in tension. Displacement changes by less than 0.11% at each step. Both stress values exceed the 394.444 MPa allowable; both displacements meet the 0.35 mm limit.

## Actual three-dimensional hotspot locations

The maximum is computed from all raw CalculiX integration-point values; no nodal averaging is used for acceptance. The nearest CAD feature was measured against the actual OpenCascade BREP face using the hotspot Gauss-point coordinate. Component order is σxx, σyy, σzz, τxy, τxz, τyz.

| Load | Element / IP | Coordinate (mm) | Stress components (MPa) | Nearest CAD face | Peak-element edge lengths (mm) | Peak-element minSICN |
|---|---|---|---|---|---|---:|
| Compression | 112448 / 1 | (30.7553, −12.5676, 11.8680) | (−521.240, −133.372, −160.718, −245.343, 1.376, −0.275) | Face 3, 1.0 mm-radius cylinder, 0.0351 mm away | 0.333–0.510 | 0.6999 |
| Tension | 111407 / 2 | (30.5739, 12.6728, 12.8472) | (579.513, 336.553, 224.717, −405.954, −1.352, −0.988) | Face 7, 1.0 mm-radius cylinder, 0.0404 mm away | 0.329–0.512 | 0.8130 |

Both peaks lie at the big-end/shank transition, close to the CAD 1 mm fillet. Across the 0.75/0.50/0.35 mm baseline sequence, the nearest-face query identifies the same 1 mm-radius CAD cylinder at distances 0.082 mm, 0.059–0.062 mm, and 0.035–0.040 mm respectively. The peak moves through the thickness with refinement and changes side with load direction while remaining in the transition region. Peak-element minSICN values across those six results range from 0.691 to 0.911; the mesh-wide minimum is lower (0.030) but does not occur in the peak elements. The closest gauge node is 33.75–35.35 mm from the global peak, so it is not a peak at a directly constrained gauge location; this distance alone cannot eliminate all boundary-condition influence. Poor quality of the peak element therefore does not explain the measured stress increase. This evidence does not establish a mathematical singularity.

The exact hotspot records, field/mesh hashes, face distances, components and element quality are in `evidence/phase3/phase3-hotspot-cad-features.json`; the fixed-region data and mesh records are in `evidence/phase3/refinement-results.json` and `runs/phase3-refinement/`. `evidence/phase3/convergence.html` plots the actual sequence. The 0.35 mm stress/displacement point clouds and local mesh ROI are generated from raw fields and saved mesh files.

## Fixed physical-region maxima

Each value below is still an unaveraged integration-point von Mises maximum, restricted by a fixed spatial mask and computed from the full field. The transition masks are ±2 mm around the nominal junction in x and ±2 mm from half shank width in |y|; bore masks are 2 mm radial bands; `pocket_shank` is the pocket's axial shank span and is not an individually isolated pocket-corner fillet. The global peak falls in the big-end transition in all six cases. No small-end, bore-band, or broad pocket-shank regional maximum approaches it in this baseline sequence.

| Target (mm) | Load | Big-end transition (MPa) | Small-end transition (MPa) | Big-bore 2 mm band (MPa) | Small-bore 2 mm band (MPa) | Pocket-shank span (MPa) |
|---:|---|---:|---:|---:|---:|---:|
| 0.75 | Compression | 519.417 | 122.690 | 253.698 | 159.974 | 146.973 |
| 0.75 | Tension | 721.779 | 274.873 | 304.156 | 220.642 | 140.050 |
| 0.50 | Compression | 545.732 | 121.666 | 255.100 | 161.977 | 146.789 |
| 0.50 | Tension | 740.474 | 291.957 | 302.615 | 221.362 | 139.632 |
| 0.35 | Compression | 566.718 | 123.356 | 255.879 | 163.893 | 147.484 |
| 0.35 | Tension | 770.139 | 274.093 | 300.675 | 220.857 | 139.274 |

The masks provide comparable global-region checks but are not a substitute for an individual geometric corner analysis. In particular, the present saved evidence does not establish a separate pocket-corner stress-convergence result. Regional raw records are saved beside each run as `regional-stress.json`.

## Limits

Richardson extrapolation and Grid Convergence Index are not reported. The levels are nonnested local unstructured meshes, only three successful points are available, and no asymptotic order or global characteristic mesh size is established. Do not apply the under-5% change as a universal criterion for other geometries or for the unqualified pin-contact model. The baseline remains structurally infeasible under its stated stress requirement.
