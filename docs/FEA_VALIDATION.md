# FEA validation



12 successful baseline comparison/refinement solves; 6 explicitly failed/over-budget attempts. These counts exclude the pilot, datasets, optimization and engine example. Filleted baseline CAD mass 735.327 g. Both bearing load directions fail the requested baseline FoS 1.8. See MESH_CONVERGENCE.md and BOUNDARY_CONDITION_COMPARISON.md.

## Experiment D — illustrative reference loads

CAD center distance is 143.5 mm to match the reference kinematics; other rod dimensions are the research design, not measured production-rod dimensions. COSINE_BEARING, global 4 mm with curve refinement. Not experimentally validated combustion.

- compression: 6575.83 N; mass 729.566 g; stress 109.955 MPa; U 0.023124 mm; FoS 6.457; runtime 110.5 s. No geometry-specific convergence established.
- tension: 1074.92 N; mass 729.566 g; stress 37.792 MPa; U 0.010486 mm; FoS 18.787; runtime 99.9 s. No geometry-specific convergence established.


See MESH_CONVERGENCE.md for exact refinement evidence. Unit tests cover force signs, resultant/moment balance, positive bearing weights, Gauss mapping, explicit failure and convergence rejection. External tests execute CAD exports and a same-mesh linear load-scaling solve. Hosted CI covers Python only.
