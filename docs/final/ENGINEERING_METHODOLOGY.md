# Engineering methodology

Units: geometry mm, force N, stress MPa, modulus MPa, density kg/mm3, CAD mass kg. Engine calculations use SI before converting resultant forces into FEA inputs. Compression is positive in the engine equilibrium; FEA signed axial force is negative for compression.

The structural model is small-displacement isotropic linear elasticity, div(sigma)+b=0 and sigma=C:epsilon. C3D10 quadratic tetrahedra use four CalculiX integration points; physical coordinates are mapped using quadratic shape functions including curved midside nodes. von Mises stress is sqrt(((sxx-syy)^2+(syy-szz)^2+(szz-sxx)^2+6*(sxy^2+sxz^2+syz^2))/2). Maximum raw integration-point stress is retained as the primary yield screen. Arithmetic mean element tensors and fixed-region maxima are supplementary and never used to hide a larger peak. Nodal stress extrapolation is not implemented or claimed.

Acceptance requires both design load cases, yield-based FoS>=1.8, displacement<=0.35mm, valid CAD/manufacturing constraints and Euler screening margin>=1.8. Euler Pcr=pi^2*E*Imin/(K*L)^2 uses K=1 and is an inexpensive pinned-pinned shank screen, not nonlinear buckling validation. Elastic stresses exceeding yield indicate failure of the design screen; they are not predictions of actual post-yield stress or plastic deformation.

Independent checks include CAD bore and section probes, volume-derived mass, force/moment and gauge reaction balance, solver coverage, reconstructed raw stress/displacement, fixed-region mesh comparisons, a uniform contact patch benchmark and literature-based engine checks. Numerical verification, model adequacy and experimental validation remain separate.
