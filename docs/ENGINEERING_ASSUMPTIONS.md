# Engineering assumptions and equations

## Geometry and axes
Global x runs between bore centers; global y spans shank width W; global z spans extrusion thickness H. Big bore is at x=0, small bore at x=L. The small-end radial wall is 0.85 times the big-end wall, preserving the legacy convention. Both rings and the shank are fused, pockets are cut symmetrically in z, and both bores cut through the final solid. Geometry validity requires a single connected solid, web H-2d >=3.5 mm and pocket width W-2tf >=4 mm. Input values are rejected, never silently clipped.

The initial solid has sharp pocket and shoulder transitions. Fillets have not been introduced without a radius/packaging design study. These corners and clamped bore edges cause stress concentrations and may produce nonconvergent local peaks. This is a research geometry, not a production-ready forged design.

Volume comes exclusively from the FreeCAD solid. Mass in kg = volume in mm³ × density in kg/mm³. STL tessellation is a display/export approximation of this solid; it does not define mass or the FEM geometry.

## Independently checked shank section
Let b=W-2tf. The pocketed section has

- A=WH-2db.
- Iy=WH³/12-2[bd³/12+bd((H-d)/2)²], integrating z² dA.
- Iz=(HW³-2db³)/12, integrating y² dA.

The brief's local Ix corresponds to global Iy here because the rod's global x is longitudinal. Tests independently decompose the section into two side walls and a middle web. The old second inertia omitted the correct side-wall parallel-axis contribution.

Axial nominal stress is F/A and uniform-shank extension is FL/(EA), with L set to center distance for this estimate. They do not capture ring compliance or bore peaks. The old empirical multipliers are archived, not described as calibrated. No analytical output is labelled a genuine FEA von Mises stress.

Euler Pcr=π² E min(Iy,Iz)/(KL)² with K=1 in both directions is a pinned-pinned uniform-shank screening assumption. Compression at or above Pcr is invalid. The optimizer also requires Pcr/F >= the specified buckling margin. This is not geometric-nonlinear or eigenvalue buckling validation. Tension has no Euler constraint. The previous capped amplification is removed.

## Material assumptions
The project preserves nominal isotropic properties: AISI 4340 steel (E=205000 MPa, ν=0.29, ρ=7.85e-6 kg/mm³, Sy=710 MPa); Ti-6Al-4V (113800, 0.34, 4.43e-6, 880); 7075-T6 aluminum (71700, 0.33, 2.81e-6, 503). These are explicitly **project assumptions**, not certified material allowables. Heat treatment, direction, temperature and batch can change strength materially. Values are configurable in `materials.py` or by constructing a validated Material input. Do not use these defaults for hardware release without material certificates.

## Reproducible academic boundary conditions
Both cases fix all translations of nodes on the big-bore cylindrical surface. Uniform global-x traction is integrated over the entire small-bore surface; force is negative x in LC1 compression and positive x in LC2 tension. Quadratic surface triangle midside weights receive one third of planar facet area; corner integrals are zero. We normalize weights to enforce the requested resultant exactly. This is an academic distributed-traction/clamp model, not frictionless pin contact. In particular it permits tensile traction over the bore.

The selected faces must be cylinders with the correct center and area/radius; there is no Face1/Face2 fallback. Applied loads and support counts are recorded. The linear-elastic model implies equal-magnitude tension/compression have equal VM and displacement magnitudes on an identical mesh; the load-scaling regression tests this.

## Mesh and outputs
Gmsh C3D10-compatible tetrahedra use curved midside nodes and high-order optimization. Conversion swaps the last two Gmsh nodes for CalculiX ordering. Numeric coordinate fields are written in bounded scientific format to avoid CalculiX input-field truncation.

The governing stress is the maximum unaveraged integration-point von Mises over all elements, including potentially singular regions. The dashboard's optional stress sample cloud plots each element's average integration-point VM at its corner centroid and is labelled accordingly. It is not a fabricated surface contour. Displacement is maximum nodal vector norm. FoS=Sy/VM. A successful solve is not equivalent to mesh-independent safety certification.

## Exclusions
No dynamic engine cycle, fatigue, nonlinear bearing contact, plasticity, thermal coupling, manufacturing residual stress, split-cap/bolt model or full nonlinear buckling. Loading is user-supplied quasi-static force, not inferred from engine RPM or combustion pressure. These exclusions must remain visible in reports and the application.

## Primary references
- [CalculiX author manual](https://www.dhondt.de/ccx_2.23.pdf): element and output conventions. The installed solver is 2.22, recorded separately.
- [Gmsh reference manual](https://gmsh.info/doc/texinfo/gmsh.html): OpenCASCADE import and quadratic meshing APIs.
- [FreeCAD release source](https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4): tested portable runtime.

Material values and academic boundary conditions are assumptions, not asserted to be validated by these software references.

Mesh minimum size is 0.45 times the requested maximum, curvature resolution 12, with two meshing threads. Seeded designs are reproducible; parallel meshing can slightly change node counts and peaks, so bitwise mesh identity is not claimed.
