# Feasibility-first lightweight selection

## Search rule

The search ranks actual CAD mass only after checking structural constraints. Two reproducible family studies generated 120 valid CAD designs; 30 mass-stratified geometries then received paired 6 mm compression/tension screens. Six promising candidates were refined. No model prediction was treated as FEA. Differential evolution, SLSQP and Bayesian optimization were not used because the high-fidelity set is too small for an evidence-backed global optimizer or surrogate constraint model.

## Feasible reference and selected design

P4-0055 is the feasible Phase 4 reference at 901.429 g. After the separate Latin-hypercube study, P4-0065 was selected at 866.860 g after refined stress, displacement, buckling and successive-mesh checks. The reduction is 34.569 g (3.835%) relative to this feasible reference.

The Phase 3 baseline is 735.327 g, but it fails both stress constraints. P4-0065 is 131.533 g (17.888%) heavier than that unsafe baseline. This is reported directly and is not described as a weight reduction. The Phase 4 result demonstrates a lighter candidate relative to a feasible Phase 4 reference, not a lighter rod than the original unsafe baseline.

The final design is the lowest-mass candidate passing the stated gates among the six refined designs, not a global mass optimum. Four other refined designs either fail tension or fail the provisional mesh-trend check. No claim is made about untested points in the 120-design CAD space.

![Actual CAD and baseline comparison](figures/phase4-cad-comparison.png)
