# Boundary conditions and contact evidence

## Primary rod model

The Phase 3 rod results use `COSINE_BEARING`: equal-and-opposite cosine-shaped radial pressure distributions at the bores, with six independent rigid-body gauge constraints. It provides internally balanced resultant loads and avoids fixing an entire bore. It remains an equivalent bearing-pressure approximation; it is not nonlinear pin contact. The historical clamped-bore model is retained separately, and changes between those models must not be attributed to geometry alone.

## Flat contact patch test

Three CalculiX 2.22 frictionless surface-to-surface penalty-contact patch tests were checked against the analytical two-block compliance. Reactions balance to better than 3 × 10⁻¹⁵; measured force differs from the analytical force by 0.124% at penalty 1 × 10⁶ MPa/mm and 0.147% at 1 × 10⁷ MPa/mm. The contact pressure is uniform over the patch. This checks a closed flat interface only; it does not validate a curved bore, contact opening, sliding, rod stress, or a connecting-rod bearing model.

## Curved pin/ring benchmark

The standalone benchmark is a 1 mm thick idealized ring (10 mm bore radius, 14 mm outer radius) and hollow pin (9.99 mm outer radius), with 0.01 mm radial clearance. It uses C3D8 bricks, one axial layer, three radial elements per body, and 32, 64, or 96 angular sectors. The ring outer surface is fixed; the thickness direction is constrained. Every pin node is prescribed to the same 0.02 mm rigid translation, rather than coupling the pin to a reference node. Contact is frictionless with a linear normal penalty. This is a solver benchmark, not a model of a connecting rod.

For the stated radial/angular/axial node ordering, the pin outer surface is C3D8 face S4 and the ring inner bore is face S6. The source CalculiX manual documents the C3D8 face numbering and contact-surface rules ([CalculiX 2.22 User's Manual, §§6.7 and 7.22–7.23](https://www.dhondt.de/ccx_2.22.pdf)). The retained input decks use those faces; `contact-validation.json` records SHA-256 hashes for the input decks, raw `.dat` results, and solver logs.

| Angular sectors | Penalty (MPa/mm) | Resultant (N) | Peak pressure (MPa) | Maximum penetration (mm) | Reaction imbalance |
|---:|---:|---:|---:|---:|---:|
| 32 | 1,000,000 | 8,682.330 | 1,182.748 | 0.001183 | (3.14\times10^{-8}) |
| 64 | 1,000,000 | 8,379.353 | 896.672 | 0.000897 | (7.34\times10^{-8}) |
| 96 | 1,000,000 | 8,312.071 | 777.121 | 0.000777 | (2.19\times10^{-8}) |
| 96 | 10,000,000 | 9,003.596 | 2,251.179 | 0.000225 | (4.37\times10^{-8}) |

Reaction equilibrium passes, but peak pressure changes by 34.3% from 32 to 96 sectors and by 189.7% when penalty is increased tenfold at 96 sectors. The resultant changes by 8.3% in the penalty comparison. These sensitivities exceed the provisional 5% target. The contact implementation is therefore **not qualified for rod integration**. The primary rod model remains `COSINE_BEARING`; no full-rod contact comparison is claimed.

Earlier surface-selection, surface-type, and contact-output parsing attempts are retained under `runs/phase3-failed-attempts/` and are excluded from the measurements above. They exposed why solver completion and reaction balance alone are insufficient validation.

## Tension-governing response

At the baseline 0.75 mm full-thickness refinement, compression is 519.417 MPa at 28,000 N (0.01855 MPa/N) and tension is 721.779 MPa at 18,000 N (0.04010 MPa/N). Tension response per unit resultant is 2.16 times larger. The opposite load signs activate opposite bore semicircles while pressure remains compressive and radial. In tension, the big-end force acts on the half-bore away from the shank, so load transfers around the ring to the shank. This is a mechanics-based interpretation of the measured hotspot fields, not an independent strain validation.
