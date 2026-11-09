# Phase 1 versus Phase 2

Phase 1 historical: sharp pockets, full big-bore clamp, uniform global traction over small bore, manual28/18 kN. Baseline734.577 g; provisional optimized384.418 g; reduction47.668%. Final1.75 mm compression352.931 MPa and U0.117279 mm; tension226.974 MPa. Peak-stress convergence was not established. Preserved branch commit1f5b5c44.

Phase 2 baseline:1 mm transition/pocket fillets, mass 735.327 g. Experiment B isolates fillets under legacy BC; C changes to compressive cosine bearing loads. D is explicitly approximate published-plot-derived illustration, not validated combustion. E is a new optimization with new labels. No47.668% result is carried forward.

Original Phase 1 baseline at4 mm: compression225.597 MPa /0.060653 mm, tension145.031 MPa /0.038988 mm. Its geometry/material/loads match the initial Phase 2 baseline except fillets. Phase 2 also adds local refinement, so this is not an isolated, converged estimate of fillet benefit. Fillets did not lower the recorded peaks or establish convergence; no stress-reduction claim is made. The source records and hashes are preserved in evidence/phase2/phase1-baseline-comparison.json.

- LEGACY_CLAMPED_BORE / compression at4 mm: 289.156 MPa, 0.060784 mm, FoS 2.4554; hotspot small-end/shank transition.
- LEGACY_CLAMPED_BORE / tension at4 mm: 191.400 MPa, 0.039061 mm, FoS 3.7095; hotspot small-end/shank transition.
- COSINE_BEARING / compression at4 mm: 462.268 MPa, 0.098823 mm, FoS 1.5359; hotspot big-end/shank transition.
- COSINE_BEARING / tension at4 mm: 632.171 MPa, 0.175587 mm, FoS 1.1231; hotspot big-end/shank transition.

The BC comparison changes ring deformation and loading direction; stresses are not interchangeable. Both Phase 2 bearing baseline cases fail FoS 1.8 and the focused refinement study does not establish converged peaks. Any new optimum is governed by the Phase 2 report, not the historical claim.
