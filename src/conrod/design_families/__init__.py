"""Phase 4 parametric connecting-rod families.

The definitions are plain Python data objects so each CAD is reproducible from
its design record.  FreeCAD is only required by :func:`build_family_rod`.
"""

import math
from dataclasses import asdict, dataclass

FAMILIES = ("i_section", "h_section", "tapered", "ribbed", "pocket_variant")
FAMILY_GEOMETRY_VERSION = "phase4-design-families-v1"


@dataclass(frozen=True)
class FamilyDesign:
    family: str = "i_section"
    length_cc: float = 145.0
    big_end_id: float = 50.0
    small_end_id: float = 24.0
    ring_thickness: float = 8.0
    shank_width: float = 30.0
    beam_thickness: float = 26.0
    flange_thickness_mm: float = 5.5
    web_thickness_mm: float = 5.0
    transition_radius_mm: float = 2.0
    taper_big_width_mm: float = 31.0
    taper_mid_width_mm: float = 27.0
    taper_small_width_mm: float = 23.0
    rib_height_mm: float = 3.0
    rib_length_mm: float = 18.0
    pocket_length_mm: float = 28.0
    pocket_width_mm: float = 12.0

    def validate(self):
        if self.family not in FAMILIES:
            raise ValueError(f"family must be one of {FAMILIES}")
        positive_ranges = {
            "length_cc": (125, 165),
            "big_end_id": (44, 56),
            "small_end_id": (20, 28),
            "ring_thickness": (6, 12),
            "shank_width": (20, 44),
            "beam_thickness": (20, 36),
            "flange_thickness_mm": (3, 10),
            "web_thickness_mm": (3, 10),
            "transition_radius_mm": (0.5, 4.0),
            "taper_big_width_mm": (20, 44),
            "taper_mid_width_mm": (20, 44),
            "taper_small_width_mm": (20, 44),
            "rib_height_mm": (0, 6),
            "rib_length_mm": (8, 35),
            "pocket_length_mm": (10, 48),
            "pocket_width_mm": (6, 20),
        }
        for name, (low, high) in positive_ranges.items():
            value = getattr(self, name)
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{name} must be finite and in [{low}, {high}]")
        if self.section_width <= self.web_thickness_mm + 6:
            raise ValueError(
                "Shank width must leave at least 3 mm on both sides of the web"
            )
        if self.beam_thickness <= 2 * self.flange_thickness_mm + 4:
            raise ValueError("Section depth must leave a web height of at least 4 mm")
        if self.transition_radius_mm >= min(
            self.ring_thickness / 2, self.flange_thickness_mm
        ):
            raise ValueError(
                "Transition radius must fit inside the eye wall and flange"
            )
        if self.pocket_length >= self.length_cc - self.big_end_id - self.small_end_id:
            raise ValueError("Pocket must remain between the eye regions")
        if self.family == "pocket_variant":
            available_pocket_width = self.shank_width - 2 * self.flange_thickness_mm - 2
            effective_pocket_width = min(self.pocket_width_mm, available_pocket_width)
            if available_pocket_width <= 0 or effective_pocket_width <= 0:
                raise ValueError(
                    "Rounded pocket must have positive clearance between the H-section flanges"
                )
            if self.pocket_length_mm < effective_pocket_width:
                raise ValueError(
                    "Rounded pocket length must be at least its effective capsule width"
                )
        for width in (
            self.taper_big_width_mm,
            self.taper_mid_width_mm,
            self.taper_small_width_mm,
        ):
            if width <= self.web_thickness_mm + 6:
                raise ValueError(
                    "Taper widths must preserve at least 3 mm per side of the web"
                )
        return self

    @property
    def section_width(self):
        if self.family == "tapered":
            return max(
                self.taper_big_width_mm,
                self.taper_mid_width_mm,
                self.taper_small_width_mm,
            )
        return self.shank_width

    @property
    def flange_thickness(self):
        return self.flange_thickness_mm

    @property
    def web_thickness(self):
        return self.web_thickness_mm

    @property
    def pocket_depth(self):
        if self.family == "i_section":
            return max((self.section_width - self.web_thickness_mm) / 2, 1.0)
        return max((self.beam_thickness - 2 * self.flange_thickness_mm) / 2, 1.0)

    @property
    def pocket_length(self):
        return self.pocket_length_mm

    @property
    def pocket_width(self):
        return self.pocket_width_mm

    @property
    def effective_pocket_width_mm(self):
        """Capsule width after reserving the modeled flange clearances."""
        return min(
            self.pocket_width_mm, self.shank_width - 2 * self.flange_thickness_mm - 2
        )

    @property
    def geometry_version(self):
        return f"{FAMILY_GEOMETRY_VERSION}:{self.family}"

    def to_dict(self):
        return asdict(self)


def _wire(points, x, App, Part):
    vertices = [App.Vector(x, y, z) for y, z in points]
    vertices.append(vertices[0])
    return Part.makePolygon(vertices)


def _section_points(family, width, depth, flange, web):
    half_w = width / 2
    if family == "h_section":
        # Two full-depth side rails joined by a centered cross web.
        return [
            (-half_w, 0),
            (-half_w, depth),
            (-half_w + flange, depth),
            (-half_w + flange, depth / 2 + web / 2),
            (half_w - flange, depth / 2 + web / 2),
            (half_w - flange, depth),
            (half_w, depth),
            (half_w, 0),
            (half_w - flange, 0),
            (half_w - flange, depth / 2 - web / 2),
            (-half_w + flange, depth / 2 - web / 2),
            (-half_w + flange, 0),
        ]
    # I section: top and bottom flanges carry bending; centered web carries shear.
    return [
        (-half_w, 0),
        (half_w, 0),
        (half_w, flange),
        (web / 2, flange),
        (web / 2, depth - flange),
        (half_w, depth - flange),
        (half_w, depth),
        (-half_w, depth),
        (-half_w, depth - flange),
        (-web / 2, depth - flange),
        (-web / 2, flange),
        (-half_w, flange),
    ]


def _profile_solid(design, App, Part):
    family = (
        "h_section" if design.family in ("h_section", "pocket_variant") else "i_section"
    )
    if design.family == "tapered":
        widths = [
            design.taper_big_width_mm,
            design.taper_big_width_mm,
            design.taper_mid_width_mm,
            design.taper_small_width_mm,
            design.taper_small_width_mm,
        ]
        xs = [
            0,
            design.length_cc * 0.16,
            design.length_cc * 0.52,
            design.length_cc * 0.86,
            design.length_cc,
        ]
        wires = [
            _wire(
                _section_points(
                    "i_section",
                    w,
                    design.beam_thickness,
                    design.flange_thickness_mm,
                    design.web_thickness_mm,
                ),
                x,
                App,
                Part,
            )
            for x, w in zip(xs, widths)
        ]
        return Part.makeLoft(wires, True, False)
    points = _section_points(
        family,
        design.section_width,
        design.beam_thickness,
        design.flange_thickness_mm,
        design.web_thickness_mm,
    )
    return Part.Face(_wire(points, 0, App, Part)).extrude(
        App.Vector(design.length_cc, 0, 0)
    )


def _rounded_box(length, width, height, corner, vector, App, Part):
    cutter = Part.makeBox(length, width, height, App.Vector(*vector))
    radius = min(corner, width * 0.45, height * 0.45)
    if radius <= 0.05:
        return cutter
    return cutter.makeFillet(radius, cutter.Edges)


def _capsule_pocket(length, width, depth, x, y, z, App, Part):
    r = width / 2
    middle = Part.makeBox(
        max(length - width, 0.1), width, depth, App.Vector(x + r, y - r, z)
    )
    left = Part.makeCylinder(r, depth, App.Vector(x + r, y, z))
    right = Part.makeCylinder(r, depth, App.Vector(x + length - r, y, z))
    return middle.fuse(left).fuse(right).removeSplitter()


def build_family_rod(design):
    """Generate a single-solid FreeCAD rod and auditable geometric metadata."""
    import FreeCAD as App
    import Part

    design.validate()
    L, H, W = design.length_cc, design.beam_thickness, design.section_width
    rb = design.big_end_id / 2 + design.ring_thickness
    rs = design.small_end_id / 2 + 0.85 * design.ring_thickness
    shank = _profile_solid(design, App, Part)
    solid = (
        shank.fuse(Part.makeCylinder(rb, H))
        .fuse(Part.makeCylinder(rs, H, App.Vector(L, 0, 0)))
        .removeSplitter()
    )

    # Fillet the geometric shank/eye intersection edges by position, never face index.
    if design.family == "tapered":
        stations = [0, L * 0.16, L * 0.52, L * 0.86, L]
        station_widths = [
            design.taper_big_width_mm,
            design.taper_big_width_mm,
            design.taper_mid_width_mm,
            design.taper_small_width_mm,
            design.taper_small_width_mm,
        ]

        def width_at(x):
            for i in range(len(stations) - 1):
                if stations[i] <= x <= stations[i + 1]:
                    f = (x - stations[i]) / (stations[i + 1] - stations[i])
                    return station_widths[i] * (1 - f) + station_widths[i + 1] * f
            return station_widths[0] if x < stations[0] else station_widths[-1]

        def root_x(radius, is_small):
            lo, hi = (L / 2, L) if is_small else (0, L / 2)
            for _ in range(60):
                mid = (lo + hi) / 2
                f = (L - mid if is_small else mid) - math.sqrt(
                    max(radius**2 - (width_at(mid) / 2) ** 2, 0)
                )
                if is_small:
                    lo, hi = (mid, hi) if f > 0 else (lo, mid)
                else:
                    lo, hi = (lo, mid) if f > 0 else (mid, hi)
            return (lo + hi) / 2

        xb, xs = root_x(rb, False), root_x(rs, True)
        root_positions = [(xb, width_at(xb)), (xs, width_at(xs))]
    else:
        root_positions = [
            (math.sqrt(max(rb * rb - (W / 2) ** 2, 0)), W),
            (L - math.sqrt(max(rs * rs - (W / 2) ** 2, 0)), W),
        ]
    roots = []
    for edge in solid.Edges:
        bb = edge.BoundBox
        if bb.YLength > 1e-6 or bb.XLength > 1e-6 or bb.ZLength < 1.0:
            continue
        for x, width in root_positions:
            if abs(bb.XMin - x) < 0.5 and abs(abs(bb.YMin) - width / 2) < 0.5:
                roots.append(edge)
                break
    if not roots:
        candidates = [
            [
                round(edge.BoundBox.XMin, 3),
                round(edge.BoundBox.YMin, 3),
                round(edge.BoundBox.ZMin, 3),
                round(edge.BoundBox.XLength, 3),
                round(edge.BoundBox.YLength, 3),
                round(edge.BoundBox.ZLength, 3),
            ]
            for edge in solid.Edges
            if edge.BoundBox.ZLength > 1
            and edge.BoundBox.XLength < 0.1
            and edge.BoundBox.YLength < 0.1
        ]
        raise ValueError(
            f"No geometric transition edges found; roots={root_positions}; candidates={candidates[:30]}"
        )
    solid = solid.makeFillet(design.transition_radius_mm, roots).removeSplitter()
    if not solid.isValid() or len(solid.Solids) != 1:
        raise ValueError("Eye transition fillet did not produce one valid solid")

    pocket_start = rb + 2
    pocket_length = min(design.pocket_length_mm, L - pocket_start - rs - 2)
    family = design.family
    if family == "pocket_variant":
        # Paired shallow capsule pockets in the H cross-web, with rounded plan ends.
        pw = design.effective_pocket_width_mm
        depth = design.web_thickness_mm * 0.22
        z_bottom = H / 2 - design.web_thickness_mm / 2 - 0.1
        z_top = H / 2 + design.web_thickness_mm / 2 - depth
        for z in (z_bottom, z_top):
            cutter = _capsule_pocket(
                pocket_length, pw, depth + 0.1, pocket_start, 0, z, App, Part
            )
            solid = solid.cut(cutter)

    if family == "ribbed":
        xroot = math.sqrt(max(rb * rb - (W / 2) ** 2, 0))
        rib_len = min(design.rib_length_mm, L * 0.35)
        h = design.rib_height_mm
        if h > 0.05:
            for sign in (-1, 1):
                y0 = sign * (W / 2 - 0.25)
                y1 = sign * (W / 2 + h)
                points = [
                    App.Vector(xroot - 1, y0, 0),
                    App.Vector(xroot + rib_len, y0, 0),
                    App.Vector(xroot + rib_len, y1, 0),
                    App.Vector(xroot + 2, sign * (W / 2 + 0.5), 0),
                ]
                wire = Part.makePolygon(points + [points[0]])
                rib = Part.Face(wire).extrude(App.Vector(0, 0, H))
                solid = solid.fuse(rib)

    for x, r in ((0, design.big_end_id / 2), (L, design.small_end_id / 2)):
        solid = solid.cut(Part.makeCylinder(r, H + 2, App.Vector(x, 0, -1)))
    solid = solid.removeSplitter()
    if not solid.isValid() or len(solid.Solids) != 1 or solid.Volume <= 0:
        raise ValueError("Family booleans did not produce one valid solid")

    bores = []
    for i, face in enumerate(solid.Faces, 1):
        surface = face.Surface
        if isinstance(surface, Part.Cylinder):
            for x, r in ((0, design.big_end_id / 2), (L, design.small_end_id / 2)):
                if (
                    abs(surface.Radius - r) < 1e-7
                    and abs(surface.Center.x - x) < 1e-7
                    and abs(surface.Center.y) < 1e-7
                    and abs(abs(surface.Axis.z) - 1) < 1e-7
                ):
                    bores.append(
                        {
                            "face": i,
                            "center_x_mm": x,
                            "diameter_mm": 2 * r,
                            "area_mm2": face.Area,
                        }
                    )
    if len(bores) != 2:
        raise ValueError(
            f"Expected two full-depth cylindrical bores, found {len(bores)}"
        )

    metadata = {
        "family": family,
        "geometry_version": design.geometry_version,
        "volume_mm3": solid.Volume,
        "center_of_mass_mm": [
            solid.Solids[0].CenterOfMass.x,
            solid.Solids[0].CenterOfMass.y,
            solid.Solids[0].CenterOfMass.z,
        ],
        "valid_topology": solid.isValid(),
        "solid_count": len(solid.Solids),
        "bore_center_distance_mm": design.length_cc,
        "bores": bores,
        "transition_radius_mm": design.transition_radius_mm,
        "transition_edges_filleted": len(roots),
        "section_width_mm": design.section_width,
        "section_depth_mm": design.beam_thickness,
        "flange_thickness_mm": design.flange_thickness_mm,
        "web_thickness_mm": design.web_thickness_mm,
        "manufacturing_note": "Single-piece forged/machined concept; no forging, tool-access, fatigue or production qualification",
    }
    return solid, metadata
