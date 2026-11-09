# Boundary conditions

The primary model remains the Phase2 cosine-bearing equivalent radial pressure approximation with equal/opposite resultants and six rigid-body gauge constraints. It is not nonlinear pin contact. Historical clamp results are retained separately; comparing different models does not isolate a geometry effect.

Three flat surface-to-surface penalty contact benchmarks executed in CalculiX2.22. Uniform pressure, balanced end reactions and analytical compliance agree within0.15%; finite-strain effects are enabled while the analytical reference is small strain. Mesh refinement from2 to4 elements per edge changes the resultant negligibly. This only validates a closed flat frictionless interface.

A separate curved pin/ring benchmark also executed: rigid hollow pin outer radius9.99mm, ring bore10mm, outer radius14mm fixed,1mm thickness, plane strain,0.01mm clearance and0.02mm prescribed pin translation. The pin is constrained directly at all its nodes; this is an explicit rigid-translation benchmark, not a reference-node implementation of an elastic pin. Separation and frictionless contact are permitted; no friction coefficient is assumed. The idealized outer clamp and pin translation do not represent a full connecting rod.

At32,64,96 angular sectors and penalty1e6MPa/mm, resultant forces were8682.330,8379.353,8312.071N; peak pressures1182.748,896.672,777.121MPa. Reaction imbalance fractions stayed below7.4e-8. At96 sectors, increasing penalty tenfold raised resultant to9003.596N and peak pressure to2251.179MPa. Resultant equilibrium alone is insufficient: peak pressure and penalty independence fail. Contact model status: NOT VALIDATED FOR ROD INTEGRATION. No full-rod contact comparison is invented.

All input decks, contact pressure/gap output, solver logs and initial input-format failures are retained. Further work requires curved-surface mesh convergence, penetration sensitivity, compliant-pin/reference-node treatment, contact-region convergence and an independent curved-contact analytical/reference solution before rod integration.

Source: [CalculiX2.22 manual](https://www.dhondt.de/ccx_2.22.pdf), sections6.7 and7.22–7.23, surface behavior keyword. These experiments are measured in `evidence/phase3/contact-validation.json`.
