# Phase 3 execution checkpoint

Active branch: feature/phase3-converged-feasible-design. Exact parent: 5e480349ba11255f6fc44e709788c542d203a096. Previous worktrees are read-only inputs.

## Budget and sequence

Historical raw DAT and JSON fields were found, and all eight focused-refinement peaks/displacements reproduced directly. No historical cases were rerun. The actual nearest CAD faces are 1mm-radius cylinders, rather than gauge constraints. Coordinate movement along the fillet and element edges comparable to its radius motivate full-thickness local refinement.

Meshing uses a single thread, fixed seed42 and explicit algorithms. Repeatability pilot has identical connectivity; maximum coordinate difference6.46e-9mm, so bitwise reproducibility is NOT claimed. Mesh and topology hashes are retained. Refinement levels are independently regenerated and not nested. Richardson/GCI estimates are not presently justified.

Structural sequence: local0.75/0.50/0.35/0.25mm; fixed physical big-end transition regions, full thickness. Preserve bulk4mm, reference geometry/material and28kN compression/18kN tension. Enforce250000nodes and600seconds per solver; stop on first failure to inspect before further expense. Raw fields/DAT/FRD retained.

Contact: three actual surface-to-surface flat patch runs pass reaction balance and analytical force within0.15%. This does NOT validate curved pin contact, separation, sliding or pin-bearing pressure. Retain cosine bearing as an equivalent-pressure approximation pending further validation.

Next: inspect complete refinement results, fixed-region stresses and resource cap; finish engine mass documentation; run staged reproducible feasibility exploration (initial pilot then40 distinct attempted geometries), paired fidelity selected from results; assess surrogate and optimization only against actual evidence.

Final completion is not yet claimed. No feasible Phase3 candidate is yet established. No previous weight-reduction claim is carried forward.

## Primary technical references

- Gmsh4.15.2 documentation: https://gmsh.info/doc/texinfo/
- CalculiX2.22 user manual, contact pair/contact print/surface behavior: https://www.dhondt.de/ccx_2.22.pdf
- Material heat-treatment dependence: https://atlassteels.com.au/wp-content/uploads/2021/09/Through-Hardening-Low-Alloy-Steel-Bar-4340-Grade-Data-Sheet-10-09-21-1.pdf
