# Phase 1 / Phase 2 / Phase 3 comparison

| Stage | Geometry, material and load model | Measured evidence | Interpretation |
|---|---|---|---|
| Phase 1 historical design | Sharp-pocket geometry; historical clamped-bore setup and manual loading | Reported optimized mass 384.418 g versus 734.577 g baseline; historical reduction 47.668% | Mesh-dependent historical result; not revalidated against Phase 3 constraints or stress convergence |
| Phase 2 baseline | 1 mm filleted-pocket geometry; assumed 4340; cosine bearing; 28/18 kN | CAD mass 735.326854 g; 4 mm compression 462.268 MPa / 0.098823 mm; tension 632.171 MPa / 0.175587 mm | Both load cases fail FoS 1.8; coarse peaks did not establish convergence |
| Phase 3 baseline | Same CAD mass and design loads; cosine-bearing equivalent pressure; full-thickness local transition refinement | At 0.35 mm: compression 566.718 MPa / 0.099087 mm; tension 770.139 MPa / 0.176078 mm. Successive stress changes are below 5% over 0.75/0.50/0.35 mm. | Limited geometry-specific convergence screen; both stresses fail allowable. The 0.25 mm mesh exceeded the node cap. No new mass reduction |
| Phase 3 nearest sampled candidate | Candidate 4; CAD mass 690.247 g; same material/load model; 0.75 mm local transition mesh | Compression 374.866 MPa / 0.093555 mm; tension 501.358 MPa / 0.147743 mm | Rejected: tension exceeds 394.444 MPa allowable, FoS 1.416. The nominal mass difference is not a validated reduction |

The historical Phase 1 reduction remains historical. Phase 1, Phase 2, and Phase 3 differ in geometry, boundary conditions, and mesh configuration; stress differences must not be attributed to geometry alone. The Phase 2 4 mm global mesh is not equivalent to the Phase 3 4 mm bulk mesh with full-thickness local transition boxes. Phase 3's successive-change criterion is not a continuum error bound.
