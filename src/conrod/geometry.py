"""One CAD construction shared by exports, meshing and visualization.
Only build_connecting_rod requires FreeCAD's Python interpreter.
"""

from .schemas import GEOMETRY_VERSION


def build_connecting_rod(g):
    import FreeCAD as App
    import Part

    g.validate()
    L, W, H = g.length_cc, g.shank_width, g.beam_thickness
    rb = g.big_end_id / 2 + g.ring_thickness
    rs = g.small_end_id / 2 + 0.85 * g.ring_thickness
    solid = Part.makeCylinder(rb, H).fuse(Part.makeCylinder(rs, H, App.Vector(L, 0, 0)))
    solid = solid.fuse(Part.makeBox(L, W, H, App.Vector(0, -W / 2, 0)))
    solid = solid.removeSplitter()
    # Vertical seam at intersection of straight shank and round ends.
    # Convex seams and cylinder seams are excluded by y and x location.
    edges = []
    for edge in solid.Edges:
        bb = edge.BoundBox
        if bb.XLength < 1e-7 and bb.YLength < 1e-7 and abs(bb.ZLength - H) < 1e-6:
            if abs(abs(bb.YMin) - W / 2) < 1e-6 and 0 < bb.XMin < L:
                edges.append(edge)
    if len(edges) != 4:
        raise ValueError(
            f"Expected four geometric shank-ring junctions, found {len(edges)}"
        )
    solid = solid.makeFillet(g.transition_radius_mm, edges)
    if not solid.isValid() or len(solid.Solids) != 1:
        raise ValueError("Shank transition fillet failed")
    for z in (-0.1, H - g.pocket_depth):
        cutter = Part.makeBox(
            g.pocket_length,
            g.pocket_width,
            g.pocket_depth + 0.1,
            App.Vector(rb + 2, -g.pocket_width / 2, z),
        )
        # Rounding every cutter edge gives both plan corners and pocket-floor blends.
        # Top of cutter extends beyond the part by radius, avoiding a lip at the mouth.
        height = g.pocket_depth + g.transition_radius_mm + 0.1
        zbase = -g.transition_radius_mm - 0.1 if z < 0 else H - g.pocket_depth
        cutter = Part.makeBox(
            g.pocket_length,
            g.pocket_width,
            height,
            App.Vector(rb + 2, -g.pocket_width / 2, zbase),
        )
        cutter = cutter.makeFillet(g.transition_radius_mm, cutter.Edges)
        if not cutter.isValid():
            raise ValueError("Pocket cutter fillet failed")
        solid = solid.cut(cutter)
    for x, r in ((0, g.big_end_id / 2), (L, g.small_end_id / 2)):
        solid = solid.cut(Part.makeCylinder(r, H + 2, App.Vector(x, 0, -1)))
    solid = solid.removeSplitter()
    if not solid.isValid() or len(solid.Solids) != 1 or solid.Volume <= 0:
        raise ValueError("CAD boolean operations did not produce one valid solid")
    # Identify cylindrical bores by radius, axis and centre; never use face numbers as fallback.
    bores = []
    for i, face in enumerate(solid.Faces, 1):
        s = face.Surface
        if isinstance(s, Part.Cylinder):
            for x, r in ((0, g.big_end_id / 2), (L, g.small_end_id / 2)):
                if (
                    abs(s.Radius - r) < 1e-7
                    and abs(s.Center.x - x) < 1e-7
                    and abs(s.Center.y) < 1e-7
                    and abs(abs(s.Axis.z) - 1) < 1e-7
                ):
                    bores.append(
                        dict(
                            face=i,
                            center_x_mm=x,
                            diameter_mm=2 * s.Radius,
                            area_mm2=face.Area,
                        )
                    )
    if len(bores) != 2:
        raise ValueError("Expected two unambiguous cylindrical bores")
    web_probe = Part.makeLine(
        App.Vector(L / 2, 0, -1), App.Vector(L / 2, 0, H + 1)
    ).common(solid)
    flange_probe = Part.makeLine(
        App.Vector(L / 2, -W, H - 0.01), App.Vector(L / 2, W, H - 0.01)
    ).common(solid)
    measured_web = web_probe.Length
    measured_flanges = sorted(edge.Length for edge in flange_probe.Edges)
    if (
        abs(measured_web - g.web_thickness) > 1e-6
        or len(measured_flanges) != 2
        or any(abs(t - g.flange_thickness) > 1e-6 for t in measured_flanges)
    ):
        raise ValueError(
            "Independent CAD section probes disagree with requested web/flanges"
        )
    return solid, dict(
        measured_web_thickness_mm=measured_web,
        measured_flange_thicknesses_mm=measured_flanges,
        volume_mm3=solid.Volume,
        valid_topology=solid.isValid(),
        solid_count=len(solid.Solids),
        bores=bores,
        web_thickness_mm=g.web_thickness,
        flange_thickness_mm=g.flange_thickness,
        transition_radius_mm=g.transition_radius_mm,
        junction_fillet_edge_count=len(edges),
        geometry_version=GEOMETRY_VERSION,
    )
