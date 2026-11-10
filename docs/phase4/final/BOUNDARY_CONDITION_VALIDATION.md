# Loads and boundary-condition validation

## Governing loads

The Phase 4 acceptance cases remain the manually specified project loads: 28,000 N compression and 18,000 N tension. They were verified against the Phase 3 configuration and were not replaced by lower illustrative engine-reconstruction forces. Engine-derived pressure demonstrations remain a separate provenance stream; they are not experimental combustion validation.

## COSINE_BEARING model

The retained model prescribes a cosine-like, frictionless radial bearing-pressure distribution on the loaded bore and an opposing distribution on the other bore. Six gauge DOFs remove rigid-body modes. The model is an equivalent pressure approximation, not a nonlinear pin/contact, bolt, friction or elastohydrodynamic solution. All candidate comparisons use the same model.

For P4-0065 at the 0.5 mm tension level, the two bore pressure resultants are +18,000 N and −18,000 N along the rod axis. The recorded force-balance fraction is 4.20e−13; the reaction residual norm is about 7.4e−12 of the constrained-DOF norm. The residual moment components are approximately (8.14e−8, 1.60e−7, 3.35e−6) N·mm. Compression and tension are solved separately.

The final mesh uses six zero-valued rigid-body gauge DOFs, while the nominal load is distributed over the cylindrical bore through the prescribed pressure approximation. Reported equilibrium confirms the discretized loads and reactions balance; it does not validate the physical contact distribution. A future contact model requires explicit pin surfaces, contact laws, friction assumptions and mesh/penalty sensitivity studies.
