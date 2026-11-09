# Final reproducible experiment record

## Shared assumptions and quantities

The design material is modeled as isotropic, linear elastic 4340 steel with (E=205\) GPa, ν=0.29 and density 7,850 kg/m³. Yield strength 710 MPa is an assumption, not a certificate or heat-treatment guarantee. The required loads are 28 kN compression and 18 kN tension, modeled separately with the cosine-bearing equivalent-pressure boundary condition. The required stress limit is 394.444 MPa (FoS 1.8); the displacement limit is 0.35 mm. Reported stresses are maximum unaveraged C3D10 integration-point von Mises values. Displacement is the maximum nodal magnitude. CAD masses are measured from FreeCAD volume and the stated density.

## Results

| Experiment | Geometry / mass | Load, support and mesh | Compression result | Tension result | Runtime / status |
|---|---|---|---|---|---|
| A: Phase 1 historical | Sharp-pocket design; 384.418 g reported, 734.577 g historical baseline | Historical clamped-bore/manual-load setup and mesh | No matched Phase 3 result | No matched Phase 3 result | Historical 47.668% reduction only; not revalidated |
| B: Phase 2 baseline | Filleted pocket; 735.326854 g | 28/18 kN, cosine bearing, 4 mm global configuration | 462.268 MPa; 0.098823 mm; FoS 1.536 | 632.171 MPa; 0.175587 mm; FoS 1.123 | ~103/~100 s; both fail FoS 1.8 |
| C: Phase 3 baseline | Same CAD; 735.326854 g | 28/18 kN, cosine bearing; 4 mm bulk, full-thickness local big-end transition target 0.35 mm; 179,366 nodes / 121,674 elements | 566.718 MPa; 0.099087 mm; FoS 1.253 | 770.139 MPa; 0.176078 mm; FoS 0.922 | 346.84/307.15 s; limited successive-change convergence screen passes, stress limits fail |
| D: Optimized candidate | None accepted | No feasible candidate reached final independent verification | Not available | Not available | Optimization objective unmet |

The nearest sampled candidate (case 4; 690.247 g) is recorded separately as a rejected screening result. At 0.75 mm transition refinement, with 80,310 nodes and 50,036 elements, it produced 374.866 MPa compression / 0.093555 mm / FoS 1.894 and 501.358 MPa tension / 0.147743 mm / FoS 1.416 (about 85.24/80.61 s). It fails the tension stress/FoS requirement and its single refined mesh does not establish convergence. Its 6.1% nominal mass difference versus baseline is not a validated reduction.

The Phase 1 value remains historical. A/B/C use differing geometry/support/mesh configurations; their stress differences do not isolate a geometry effect. Phase C's stress convergence is limited to the tested baseline and local refinement sequence. The 0.25 mm mesh exceeded the 250,000-node budget. The curved contact benchmark is not qualified for rod integration, so all Phase 2/3 rod stresses use the stated cosine-bearing approximation.
