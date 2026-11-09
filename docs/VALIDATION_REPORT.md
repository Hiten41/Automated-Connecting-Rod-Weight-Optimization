# Phase 2 validation report

Research prototype; no mechanically qualified design.

## Engine reference

Approximate published-plot-derived peak compression 6575.83 N at 25.00 degrees; tension 1074.92 N at 380.00 degrees. Independently plotted rod-force peak approximately 7200 N; sparse-point comparison MAE 412.61 N. This mismatch is not concealed or fitted away. Exact derivative versus finite-difference maximum error 0.000186385 m/s². TDC/BDC positions reproduce0/86 mm. See ENGINE_LOAD_MODEL.md for sources, mass definition and missing raw pressure data. Combustion loading is NOT experimentally validated.

## Actual FEA

12 successful baseline comparison/refinement solves; 6 explicitly failed/over-budget attempts. These counts exclude the pilot, datasets, optimization and engine example. Filleted baseline CAD mass 735.327 g. Both bearing load directions fail the requested baseline FoS 1.8. See MESH_CONVERGENCE.md and BOUNDARY_CONDITION_COMPARISON.md.

## Experiment D — illustrative reference loads

CAD center distance is 143.5 mm to match the reference kinematics; other rod dimensions are the research design, not measured production-rod dimensions. COSINE_BEARING, global 4 mm with curve refinement. Not experimentally validated combustion.

- compression: 6575.83 N; mass 729.566 g; stress 109.955 MPa; U 0.023124 mm; FoS 6.457; runtime 110.5 s. No geometry-specific convergence established.
- tension: 1074.92 N; mass 729.566 g; stress 37.792 MPa; U 0.010486 mm; FoS 18.787; runtime 99.9 s. No geometry-specific convergence established.

## ML

120 compatible records; selected mlp; held-out metrics and limitations in ML_EVALUATION.md.

## Optimization

Status: **NO_VERIFIED_FEASIBLE_DESIGN**. New multistart optimization used Phase 2 geometry/BC/labels. Baseline mass: 0.7353268536526627; optimized mass: None; reduction: None. Missing values mean no accepted new design, not zero mass or zero error.

Recorded starts: 5; optimizer-admitted FEA verification attempts: 0. All candidate reasons and margins are retained in evidence/phase2/phase2-optimization-optimization.json. Mesh-dependent passes are provisional, never hardware qualification.

### Independent checks of rejected optimizer points

These are diagnostic designs, not accepted optima or qualified hardware. No mass-reduction claim follows from an optimizer failure.

Candidate 1: single-mesh constraint pass=False; rejection reasons=['tension_stress_mpa violated'].

- compression: mass 764.789 g; stress 350.048 MPa; U 0.078030 mm; FoS 2.028.
- tension: mass 764.789 g; stress 490.912 MPa; U 0.120690 mm; FoS 1.446.

Candidate 2: single-mesh constraint pass=False; rejection reasons=['tension_stress_mpa violated'].

- compression: mass 904.047 g; stress 388.802 MPa; U 0.068254 mm; FoS 1.826.
- tension: mass 904.047 g; stress 531.549 MPa; U 0.118725 mm; FoS 1.336.

## Quality and limitations

Actual FreeCAD FEM imports pass preflight. Python tests and external integration evidence are recorded separately. Browser inspection is blocked by `Local browser use is disabled in Work settings`; functional AppTest/HTTP checks do not replace visual QA. No screenshots fabricated. Raw input decks/logs/fields remain locally reproducible; portable compact evidence includes source hashes when packaged. Phase 1 and upstream histories are preserved. Remaining issues: unconverged peaks, approximate pressure reference, small coarse-data ML domain, no fatigue/contact/thermal/plastic/nonlinear stability certification.
