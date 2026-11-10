# Limitations and remaining engineering work

1. **Material condition:** 710 MPa remains a historical yield assumption. No component-specific 4340 forging certificate, heat-treatment record, hardness map or coupon test is available.
2. **Loads:** 28 kN compression and 18 kN tension are prescribed design loads. Engine-derived illustrations are not raw experimental cylinder-pressure measurements and do not replace these loads.
3. **Bearing/contact:** COSINE_BEARING is an equivalent frictionless radial pressure with six rigid-body gauge DOFs. No nonlinear pin, bolt, friction or clearance contact model is validated.
4. **Mesh:** final 0.75→0.50 mm peak-stress changes are below 5%, but meshes are nonnested and no GCI/continuum bound is established. The stress hotspot is localized at a finite fillet; further refinement may change the pointwise maximum.
5. **Buckling:** the reported factor is linear eigenvalue bifurcation only. Geometric imperfections, residual stress, material plasticity and nonlinear postbuckling are not represented.
6. **Fatigue:** no component S–N curve, validated alternating stress history, surface/process correction or target life is available. No fatigue-life claim is made.
7. **Manufacturing:** CAD topology and clear bores are checked, but forging flow, die design, machining reach, tolerances, surface finish, residual stress and production qualification are not.
8. **Optimization:** P4-0065 is lowest-mass among the six refined candidates passing the stated checks, not a global optimum. 120 valid CAD solids and 30 paired coarse candidates are a finite sample.
9. **Topology:** no density-based SIMP solver or density field was implemented. The work is topology-inspired parametric family exploration.
10. **Machine learning:** grouped coarse and fine-holdout errors are too large relative to constraint margin for constraint enforcement. All final checks use actual FEA.
11. **GUI verification:** see [Website QA](WEBSITE_QA.md) for the local app and browser inspection result.
