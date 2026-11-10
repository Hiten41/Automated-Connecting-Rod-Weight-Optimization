# Parametric geometry family study

Five editable FreeCAD families were added under `src/conrod/design_families/`. Every accepted CAD record contains a one-solid validity check, actual volume/mass, bore dimensions and center distance. All preserve the nominal 145 mm center distance and 50/24 mm bores.

| Family | Material layout and controls | LHS coarse sample, median compression / tension peak (MPa) | Coarse pairs below allowable* |
|---|---|---:|---:|
| I-section | Top/bottom flanges and central web; width, depth, flange/web thickness, transition radius | 361.4 / 478.8 | 0/6 |
| H-section | Two full-depth side rails joined by a centered web | 222.0 / 332.3 | 4/6 |
| Tapered | Smooth loft through five axial stations with interpolated width | 477.4 / 591.3 | 1/6 |
| Ribbed | Local ribs in the junction region with controllable height and run | 408.5 / 619.4 | 0/6 |
| Rounded pocket variant | H-section web with paired rounded capsule pockets | 192.9 / 268.5 | 5/6 |

\*These are 6 mm screen results from three mass-stratified designs in each study, not final feasibility results. The Phase 4 LHS screen found multiple coarse passes that did not survive refinement; coarse FEA is never used to declare feasibility.

The new families support actual CAD volume and mass calculations. They are design concepts, not manufacturing-qualified forgings: no die design, forging flow, machining access, fatigue, residual stress, material certificate or tolerance analysis is included. The tapered loft is smooth and valid as CAD, but production draft, parting line and grain flow remain unassessed.

The strongest verified result is a rounded-pocket variant, P4-0065, with 866.860 g CAD mass and a 1.317 mm transition radius. Its raw 0.5 mm local-mesh stress peak is 366.006 MPa in tension and occurs at the big-end/shank transition. Family-level metrics and all coarse labels are in `data/phase4/family-screen.json` and `data/phase4/fea-dataset.jsonl`.
