# FEA results

Material: isotropic linear 4340 model, E205GPa, nu.29, density7850kg/m3 and assumed yield710MPa. The yield is not backed by a material certificate. COSINE_BEARING applies compressive radial pressure integrated to equal/opposite net loads with six rank-checked rigid-body gauge constraints; no nonlinear contact is used. CalculiX2.22 C3D10 four-point integration stress is reported without nodal averaging.

Baseline geometry is735.326854g by CAD. At the locally refined4mm bulk mesh with full-thickness big-end-transition field, 0.35mm target solved with179366 nodes/121674 elements. Compression28000N: peak IP VM566.718MPa, U.099087mm, FoS1.253. Tension18000N:770.139MPa, U.176078mm, FoS.922. Both displacement screens pass and both yield/FoS screens fail. Peak elements' minSICN are .700 and .813; quality does not identify a low-quality peak element.

The same-geometry refinement criterion is met across .75/.50/.35mm for both peaks and displacement. It is a provisional successive-change criterion; .25mm exceeded the node limit. The baseline is therefore best-supported under the tested local sequence but stress remains above allowable. See mesh and boundary reports for all levels, provenance and caveats.

Interactive visualizations generated from the actual retained fields are `evidence/phase3/0.35-compression-stress.html`, `0.35-tension-stress.html`, the matching displacement views, and `0.35-tension-mesh-hotspot.html`. Stress is displayed as deterministically thinned unaveraged integration-point markers; the extracted peak and red marker are computed from the complete solver field. Displacement is nodal magnitude on a geometry deformed by a labeled display scale of 100. The mesh-region view uses the saved quadratic tetrahedral Gmsh mesh, not a smoothed stress contour. Provenance sidecars record field and mesh hashes.

The nearest feasibility-search candidate (case 4) has one 0.75 mm transition-refinement result per load case: 374.866 MPa compression and 501.358 MPa tension. It is rejected on tension FoS 1.416. These two solves are a candidate screen, not a converged optimized-design result.
