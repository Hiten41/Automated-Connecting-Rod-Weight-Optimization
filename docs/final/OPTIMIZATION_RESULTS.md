# Optimization results

## Objective and constraints

The objective is minimum measured FreeCAD CAD mass with separate 28 kN compression and 18 kN tension checks. Constraints are maximum stress 394.444 MPa (710 MPa assumed yield / FoS 1.8), maximum displacement 0.35 mm, Euler shank screening margin at least 1.8, valid geometry and supported bounds. No candidate is accepted from surrogate predictions alone; final acceptance needs actual CAD and independent refined FEA with defensible convergence.

## Feasibility and candidate outcome

The 40-point seeded Latin-hypercube study found zero coarse-screen passes among 35 valid CAD/FEA geometries; five more candidates failed CAD validation. The nearest sampled case is index 4 at 690.247 g. It passes compression at its 0.75 mm refinement (374.866 MPa, FoS 1.894) but fails tension at 501.358 MPa, FoS 1.416. It is rejected. Its 6.1% lower nominal CAD mass than baseline is not a verified reduction. The 40 samples do not prove global infeasibility.

## Optimizer decision

The completed 12-geometry paired-fidelity dataset gives only three held-out geometry groups. The validation-selected MLP's held-out stress MAE is 208.86 MPa, RMSE 291.95 MPa and R² 0.031; only two test analyses lie near the exploratory constraint region, with stress MAE 56.29 MPa and negative R². Ridge and Extra Trees perform worse on held-out stress. The model is recorded as `EXPLORATORY_SCREENING_ONLY` and the Phase 3 optimizer/API and UI now reject it as an optimization input until held-out evidence supports that use.

No Phase 3 Differential Evolution/SLSQP search was run, because the feasibility screen supplied no feasible starting design and the available model did not pass its held-out evaluation. No candidate was admitted to optimization FEA verification, no global optimum is claimed, and there is no optimization history plot. The machine-readable decision, study counts and held-out metrics are in `data/phase3/optimization/decision.json`. This is a deliberate evidence-based stop, not a surrogate result. The rejection is covered by automated tests.

## Conclusion

**No feasible Phase 3 optimized candidate is accepted; the lightweight design objective remains unmet.** The governing observed constraint is big-end/shank transition stress, especially tension. Broader design exploration should first justify any extension of the ring/transition bounds, add geometry-diverse paired fine data, and require actual FEA on any proposed candidate. The small sample leaves the rest of the bounded domain inconclusive. Phase 2's five unsuccessful SLSQP starts and two tension-failing diagnostic designs remain historical results only.
