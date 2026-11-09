# Phase 2 engineering assumptions

Historical Phase 1 assumptions remain unchanged under `docs/phase1/` and on the preserved branch.

Units are mm/N/MPa in CAD/FEA and SI in engine mechanics. Materials are isotropic linear elastic; yield FoS=tabulated yield/maximum unaveraged integration-point von Mises stress. Material values are screening inputs, not certified heat-treatment allowables. No fatigue, thermal residual stress, plasticity, dynamic amplification, oil film, bolt/cap split, contact separation or nonlinear buckling is modeled.

Geometry is one valid FreeCAD solid, version rod-2-filleted-pocket. Four shank/ring junction edges are selected by coordinate and orientation, never hardcoded indices, and filleted. Pocket cutters have rounded plan and floor transitions. Baseline radius1 mm is constrained below pocket depth, half pocket width and half ring wall; it is fixed during the five-variable optimization. Radius candidates0.5,1,1.5,2 mm were executed successfully for the baseline;3 mm is explicitly invalid. Independent section probes verify web/flanges. Bore radii/centers/areas are checked after booleans. These are geometric feasibility rules, not industrial process tolerances.

Quadratic C3D10 tetrahedra use curved midside coordinates. Gmsh and CalculiX edge ordering differs and is converted explicitly. Mesh quality includes minimum and1st-percentile minSICN; nonpositive values fail. Peak stress remains unfiltered. The moving2 mm-neighborhood IP mean is descriptive only, not a qualification metric.

Euler buckling is a nominal screening constraint with idealized section and end assumptions. It is not a nonlinear stability analysis. Multistart SLSQP minimizes actual CAD mass within a learned response domain. It cannot certify a global optimum. A successful solver run, a surrogate constraint pass, a refined-mesh constraint pass and engineering qualification are distinct outcomes.

See ENGINE_LOAD_MODEL.md and BOUNDARY_CONDITION_COMPARISON.md for force derivations and limitations. No design is mechanically qualified unless appropriate geometry-specific convergence is demonstrated.
