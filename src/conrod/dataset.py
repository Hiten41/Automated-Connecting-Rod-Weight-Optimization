import json
import math
import time
from pathlib import Path
from scipy.stats import qmc
from .schemas import Geometry, LoadCase, MeshSettings, BOUNDS, GEOMETRY_VERSION
from .materials import MATERIALS
from .fea import solve, fingerprint, configuration
import hashlib


def validate_record(r, simulation_version="phase2-bearing-v1"):
    if (
        r.get("geometry_version") != GEOMETRY_VERSION
        or r.get("simulation_version") != simulation_version
    ):
        raise ValueError("Incompatible geometry/simulation provenance")
    if (
        r.get("status") != "FEA_SUCCESS"
        or r.get("data_source") != "FreeCAD/Gmsh/CalculiX"
    ):
        raise ValueError("Not verified solver data")
    Geometry(**r["geometry"]).validate()
    from .schemas import Material

    Material(**r["material"]).validate()
    LoadCase(**r["load"]).validate()
    MeshSettings(**r["mesh"]).validate()
    for key in [
        "mass_kg",
        "max_von_mises_mpa",
        "max_displacement_mm",
        "factor_of_safety",
        "node_count",
        "element_count",
    ]:
        if not math.isfinite(r[key]) or r[key] <= 0:
            raise ValueError(f"Invalid {key}")
    if (
        not r.get("solver_version")
        or not r.get("geometry_version")
        or not r.get("fields_path")
    ):
        raise ValueError("Missing provenance")
    if not math.isclose(
        r["factor_of_safety"],
        r["material"]["yield_strength_mpa"] / r["max_von_mises_mpa"],
        rel_tol=1e-8,
    ):
        raise ValueError("Inconsistent FoS")
    return r


def load_verified(path):
    records = []
    seen = set()
    version = None
    for line in Path(path).read_text().splitlines():
        raw = json.loads(line)
        if version is None:
            version = raw.get("simulation_version")
            if version not in ("phase2-bearing-v1", "phase3-deterministic-bearing-v1"):
                raise ValueError("Unsupported simulation version")
        r = validate_record(raw, version)
        if r["sample_id"] in seen:
            raise ValueError("Duplicate simulation ID")
        seen.add(r["sample_id"])
        records.append(r)
    return records


def generate(output, count=12, seed=42, size_mm=5.0, fixed_packaging=True):
    """Count is number of geometries; both load cases are run per geometry.
    Resuming reuses only matching successful result records; failures remain in manifest.
    """
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    sampler = qmc.LatinHypercube(d=10, seed=seed)
    materials = list(MATERIALS.values())
    accepted = []
    rejected = 0
    batch = iter(sampler.random(count))
    while len(accepted) < count:
        try:
            sample = next(batch)
        except StopIteration:
            batch = iter(sampler.random(max(count - len(accepted), 1)))
            sample = next(batch)
        values = {
            k: lo + (hi - lo) * sample[i]
            for i, (k, (lo, hi)) in enumerate(BOUNDS.items())
        }
        values["transition_radius_mm"] = 1.0
        if fixed_packaging:
            values.update(length_cc=145.0, big_end_id=50.0, small_end_id=24.0)
        try:
            g = Geometry(**values).validate()
        except ValueError:
            rejected += 1
            continue
        accepted.append((g, materials[len(accepted) % len(materials)], sample[8:]))
    records = []
    failed = []
    start = time.perf_counter()
    for i, (g, m, loads) in enumerate(accepted):
        for j, kind in enumerate(("compression", "tension")):
            load = LoadCase(kind, 15000 + 30000 * loads[j])
            mesh = MeshSettings(size_mm)
            case = fingerprint(
                dict(
                    geometry_version=GEOMETRY_VERSION,
                    simulation_version="phase3-deterministic-bearing-v1",
                    solver_sha256=hashlib.sha256(
                        Path(configuration()["ccx"]).read_bytes()
                    ).hexdigest()
                    if Path(configuration()["ccx"]).is_file()
                    else "unavailable",
                    geometry=g.to_dict(),
                    material=m.to_dict(),
                    load=load.to_dict(),
                    mesh=mesh.to_dict(),
                )
            )[:20]
            folder = output / "cases" / case
            existing = folder / "result.json"
            r = json.loads(existing.read_text()) if existing.exists() else None
            if (
                not r
                or r.get("status") != "FEA_SUCCESS"
                or r.get("geometry_version") != GEOMETRY_VERSION
                or r.get("simulation_version") != "phase3-deterministic-bearing-v1"
                or r.get("mesh") != mesh.to_dict()
            ):
                r = solve(g, m, load, mesh, folder)
            try:
                records.append(validate_record(r, "phase3-deterministic-bearing-v1"))
            except (ValueError, KeyError) as exc:
                failed.append(dict(result=r, quarantine_reason=str(exc)))
            (output / "verified.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in records)
            )
            (output / "failures.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in failed)
            )
            print(f"{i + 1}/{count} {kind}: {r['status']}", flush=True)
    report = dict(
        geometries=count,
        successful_analyses=len(records),
        failed_analyses=len(failed),
        rejected_geometry_samples=rejected,
        seed=seed,
        sampling_method="Batch Latin Hypercube with rejection replenishment",
        geometry_version=GEOMETRY_VERSION,
        simulation_version="phase3-deterministic-bearing-v1",
        boundary_mode="COSINE_BEARING",
        load_provenance="Sampled manual axial forces; actual FEA labels, not measured combustion",
        fixed_transition_radius_mm=1.0,
        fixed_packaging=fixed_packaging,
        elapsed_s=time.perf_counter() - start,
        mesh_size_mm=size_mm,
    )
    (output / "manifest.json").write_text(json.dumps(report, indent=2))
    return report
