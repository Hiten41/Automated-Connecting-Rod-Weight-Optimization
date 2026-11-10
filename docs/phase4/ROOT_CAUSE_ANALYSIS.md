# Phase 3 failure root cause

## Finding

The Phase 3 rod fails because its big-end-to-shank transition carries a concentrated, multiaxial load through a small finite-radius junction. The global stress peak is at this transition in both load directions. It is not at the bore surface or in the uniform shank. Increasing gross shank area alone therefore does not address the dominant load-transfer problem.

## Baseline and load path

The Phase 3 CAD mass is 735.327 g, with 145 mm center distance, 50/24 mm big/small bores, 25 mm rod width, 22 mm depth, 8 mm ring wall, 2.2 mm face pockets and a nominal 1 mm transition fillet. The material and analysis inputs are the project assumptions: linear-elastic 4340 steel, E=205 GPa, ν=0.29, density=7850 kg/m³, 710 MPa yield, compression 28 kN, tension 18 kN, and the 394.444 MPa allowable for FoS 1.8.

Load transfers from each cosine-bearing bore pressure through the eye wall, into the eye/shank junction, through the shank, and into the opposite eye. The equivalent pressure distribution and six rigid-body gauge DOFs are equilibrated, but the model is not nonlinear pin contact. Phase 3 reactions balance the prescribed force to approximately 1e-9 N and moments to approximately 1e-6 N·mm.

## Raw hotspot evidence

The values below are maximum **unaveraged integration-point** von Mises stresses from the 0.35 mm local refinement. Integration-point tensors use the order xx, yy, zz, xy, xz, yz, in MPa.

| Case | Peak (MPa) | Coordinates (mm) | Tensor (MPa) | Principal stresses (MPa) |
|---|---:|---|---|---|
| Compression, 28 kN | 566.718 | (30.7553, -12.5676, 11.8680) | (-521.240, -133.372, -160.719, -245.343, 1.376, -0.275) | (-640.044, -160.720, -14.565) |
| Tension, 18 kN | 770.139 | (30.5739, 12.6728, 12.8472) | (579.513, 336.553, 224.717, -405.954, -1.352, -0.988) | (34.279, 224.730, 881.774) |

Both peaks lie on the big-end/shank transition, within about 0.04 mm of the nominal cylindrical fillet face and about 8 mm from the big-bore cylindrical surface. Their 2 mm neighborhoods have descriptive unweighted IP means of about 210.6 MPa in compression and 281.4 MPa in tension. These neighborhood means are diagnostic only; acceptance uses the raw peak. Local edges near the peaks are about 0.33–0.51 mm. The peak elements are not identified as the lowest-quality elements in the sidecar audit.

## Why area-only screening is misleading

The baseline shank section is approximately 25×22 mm before removing two 14×2.2 mm face pockets, leaving a simplified net axial area of about 488.4 mm². Nominal axial stresses are therefore roughly 57.3 MPa at 28 kN and 36.9 MPa at 18 kN, far below the computed transition peaks. Ratios of peak to nominal stress are not handbook stress-concentration factors: the FEA includes eye stiffness, bearing-pressure load transfer, local bending and a three-dimensional filleted junction, while the nominal estimate does not.

The transition is finite-radius and physically meaningful in the CAD model, but the maximum remains gradient-sensitive. The Phase 3 nonnested 0.75/0.50/0.35 mm sequence showed a provisional trend only; the 0.25 mm solve exceeded the node budget. No continuum error bound or proof of a mathematical singularity was established.

## Engineering interpretation

The primary cause is an unfavorable eye-to-shank load path and limited transition stiffness under the stated bearing approximation. The 1 mm transition radius and section layout concentrate stress where the load leaves the big eye. The tension case is more severe because its load direction and stress tensor produce a larger local multiaxial response. Displacement is not the baseline failure: both values are below 0.35 mm, while the stresses exceed the 394.444 MPa allowable.

This diagnosis motivated wider transition support, explicit I/H section families, smooth tapers, ribs, and rounded pocket variants. The Phase 4 result is documented separately; the Phase 3 baseline remains an unsafe mass reference.

## Related evidence

- [Phase 4 final design validation](final/FINAL_DESIGN_VALIDATION.md)
- [Raw Phase 4 integration-point contours](final/figures/phase4-tension-ip-stress.png)
- [Mesh response](final/figures/phase4-mesh-trend.png)
