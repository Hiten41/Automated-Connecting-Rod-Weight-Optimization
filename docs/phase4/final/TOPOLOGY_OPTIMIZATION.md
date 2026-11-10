# Topology-inspired redesign, not SIMP optimization

## Capability audit

The installed project stack supports parametric FreeCAD solids, Gmsh meshing, linear static and eigenvalue buckling analyses in CalculiX, plus Python scientific and machine-learning packages. The local portable Python runtime did not contain `dolfin`, `fenics` or `ufl`; FreeCAD FEM did not provide a working density-based topology optimizer in the audited installation. No SIMP density field, volume-fraction iterations, density filter, sensitivity field or topology reconstruction was produced.

## Implemented alternative

The implemented alternative is structured, topology-inspired parametric material redistribution across I, H, tapered, ribbed and rounded-pocket families. The bore and bearing interfaces remain non-design geometry; the shank, eye transitions and pocket layout vary within validated CAD bounds. Actual solid geometry, actual CAD mass and CalculiX fields are evaluated for selected candidates.

This is a family-based geometry search. It is not a mathematical topology optimization and no density map or global topology optimum is claimed. The distinction is retained in the RodLab page and reports. The next technically supportable step would be to establish a validated density-based solver and reconstruction workflow, then revalidate reconstructed CAD with the same actual-FEA gates.
