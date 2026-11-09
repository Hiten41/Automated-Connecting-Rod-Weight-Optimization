from typing import TypedDict
from dataclasses import dataclass, asdict
from enum import Enum
import math

GEOMETRY_VERSION = "rod-2-filleted-pocket"
BOUNDS = dict(
    length_cc=(125.0, 165.0),
    big_end_id=(44.0, 56.0),
    small_end_id=(20.0, 28.0),
    ring_thickness=(4.5, 9.0),
    shank_width=(15.0, 28.0),
    beam_thickness=(14.0, 24.0),
    pocket_depth=(2.0, 6.0),
    flange_thickness=(2.5, 6.0),
    transition_radius_mm=(0.5, 3.0),
)
OPT_KEYS = tuple(list(BOUNDS)[3:8])


class Mode(str, Enum):
    ANALYTICAL = "ANALYTICAL"
    CAD_ONLY = "CAD_ONLY"
    FEA = "FEA"


@dataclass(frozen=True)
class Geometry:
    length_cc: float = 145.0
    big_end_id: float = 50.0
    small_end_id: float = 24.0
    ring_thickness: float = 8.0
    shank_width: float = 25.0
    beam_thickness: float = 22.0
    pocket_depth: float = 2.2
    flange_thickness: float = 5.5
    transition_radius_mm: float = 1.0

    def validate(self):
        for key, (lo, hi) in BOUNDS.items():
            value = getattr(self, key)
            if not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f"{key} must be finite and in [{lo}, {hi}] mm")
        if self.web_thickness < 3.5 or self.pocket_width < 4:
            raise ValueError("Require web >= 3.5 mm and pocket width >= 4 mm")
        if self.transition_radius_mm >= min(
            self.pocket_depth, self.pocket_width / 2, self.ring_thickness / 2
        ):
            raise ValueError(
                "Fillet radius must be smaller than pocket depth, half width and half ring wall"
            )
        if self.pocket_length <= 5:
            raise ValueError("Pockets must lie between the ends")
        return self

    @property
    def web_thickness(self):
        return self.beam_thickness - 2 * self.pocket_depth

    @property
    def pocket_width(self):
        return self.shank_width - 2 * self.flange_thickness

    @property
    def pocket_length(self):
        return (
            self.length_cc
            - self.big_end_id / 2
            - self.small_end_id / 2
            - 1.85 * self.ring_thickness
            - 4
        )

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Material:
    name: str
    youngs_modulus_mpa: float
    poissons_ratio: float
    density_kg_per_mm3: float
    yield_strength_mpa: float

    def validate(self):
        vals = (
            self.youngs_modulus_mpa,
            self.poissons_ratio,
            self.density_kg_per_mm3,
            self.yield_strength_mpa,
        )
        if (
            not all(math.isfinite(v) for v in vals)
            or min(vals[0], vals[2], vals[3]) <= 0
            or not -1 < vals[1] < 0.5
        ):
            raise ValueError("Invalid isotropic material")
        return self

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class LoadCase:
    kind: str = "compression"
    force_n: float = 28000.0

    def validate(self):
        if (
            self.kind not in ("compression", "tension")
            or not math.isfinite(self.force_n)
            or self.force_n <= 0
        ):
            raise ValueError("Use compression/tension and a positive finite force")
        return self

    @property
    def signed_force(self):
        return self.force_n * (-1 if self.kind == "compression" else 1)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class MeshSettings:
    size_mm: float = 5.0
    order: int = 2
    boundary_mode: str = "COSINE_BEARING"
    local_refinement: bool = True
    hotspot_size_mm: float | None = None
    refinement_region: str = "all_features"

    def validate(self):
        if self.refinement_region not in ("all_features", "big_end_transition"):
            raise ValueError("Unknown refinement region")
        if self.hotspot_size_mm is not None and (
            not math.isfinite(self.hotspot_size_mm)
            or not 0 < self.hotspot_size_mm <= self.size_mm
        ):
            raise ValueError("Local size must be positive and <= global size")
        if self.boundary_mode not in ("COSINE_BEARING", "LEGACY_CLAMPED_BORE"):
            raise ValueError("Unknown boundary condition")
        if not math.isfinite(self.size_mm) or self.size_mm <= 0 or self.order != 2:
            raise ValueError("Positive mesh size and quadratic tetrahedra required")
        return self

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Constraints:
    min_fos: float = 1.8
    max_displacement_mm: float = 0.35
    min_buckling_margin: float = 1.8

    def validate(self):
        if (
            not all(math.isfinite(v) and v > 0 for v in asdict(self).values())
            or self.min_fos < 1
            or self.min_buckling_margin < 1
        ):
            raise ValueError("Invalid safety constraints")
        return self


# Explicit output contracts. Optional fields depend on the recorded status;
# failed FEA never supplies successful structural response fields.


class AnalyticalResult(TypedDict, total=False):
    status: str
    valid: bool
    estimated_nominal_stress_mpa: float
    estimated_displacement_mm: float
    estimated_factor_of_safety: float
    buckling_margin: float | None
    mass_kg: float | None
    mass_source: str
    assumptions: list[str]


class FEAResult(TypedDict, total=False):
    status: str
    sample_id: str
    geometry: dict[str, float]
    material: dict
    load: dict
    mesh: dict
    geometry_version: str
    data_source: str
    mass_kg: float
    max_von_mises_mpa: float
    max_displacement_mm: float
    factor_of_safety: float
    node_count: int
    element_count: int
    solver_version: str
    fields_path: str
    output_dir: str
    error: str
    runtime_s: float


class OptimizationResult(TypedDict, total=False):
    status: str
    baseline_mass_kg: float
    optimized_mass_kg: float
    mass_reduction_pct: float
    constraints: dict[str, float]
    stress_guard_factor: float
    diagnostics: list[dict]
    verification_attempts: list[dict]
    result: dict | None
    error: str
