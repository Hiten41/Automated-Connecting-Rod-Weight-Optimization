"""Auditable CAD -> STEP -> Gmsh -> CalculiX pipeline. No fallback."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
import numpy as np
from .schemas import (
    Geometry,
    Material,
    LoadCase,
    MeshSettings,
    GEOMETRY_VERSION,
    Mode,
    FEAResult,
    AnalyticalResult,
)
from .materials import mass_from_volume

ROOT = Path(__file__).resolve().parents[2]


def fingerprint(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def configuration():
    path = ROOT / "local_config.json"
    cfg = json.loads(path.read_text()) if path.exists() else {}
    for key in ("freecad_python", "ccx"):
        cfg[key] = os.environ.get("CONROD_" + key.upper(), cfg.get(key, ""))
    cfg["ccx"] = cfg["ccx"] or shutil.which("ccx") or ""
    return cfg


def command(args, cwd, log, timeout=300):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    env["CCX_NPROC_RESULTS"] = "2"
    try:
        result = subprocess.run(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        Path(log).write_text(
            output + "\nTIMEOUT after " + str(timeout) + " seconds", encoding="utf-8"
        )
        raise RuntimeError(f"External process timed out; see {log}") from exc
    Path(log).write_text(result.stdout, encoding="utf-8")
    if result.returncode and not (
        str(args[-1]) == "-v" and "This is Version" in result.stdout
    ):
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")
    return result.stdout


def cad(g, out, preflight=False):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg = configuration()
    if not cfg["freecad_python"] or not Path(cfg["freecad_python"]).is_file():
        raise RuntimeError(
            "Configure CONROD_FREECAD_PYTHON to bundled FreeCAD python.exe"
        )
    request = dict(geometry=g.to_dict(), output_dir=str(out), preflight=preflight)
    (out / "cad-request.json").write_text(json.dumps(request))
    command(
        [
            cfg["freecad_python"],
            ROOT / "workers/freecad_worker.py",
            out / "cad-request.json",
        ],
        out,
        out / "cad.log",
    )
    result = json.loads((out / "cad.json").read_text())
    if result["status"] not in ("CAD_SUCCESS", "PREFLIGHT_SUCCESS"):
        raise RuntimeError(result.get("error", "CAD failed"))
    return result


def preflight(out=None):
    out = Path(out or ROOT / "runs/preflight")
    out.mkdir(parents=True, exist_ok=True)
    report = {"python": sys.version, "configuration": configuration(), "checks": {}}
    try:
        (out / "write-test.txt").write_text("ok")
        report["checks"]["writable"] = True
        report["freecad"] = cad(Geometry(), out, preflight=True)
        report["checks"]["freecad_fem"] = True
    except Exception as exc:
        report["checks"]["freecad_fem"] = False
        report["freecad_error"] = str(exc)
    try:
        import gmsh

        report["gmsh_version"] = gmsh.__version__
        report["checks"]["gmsh"] = True
    except Exception as exc:
        report["checks"]["gmsh"] = False
        report["gmsh_error"] = str(exc)
    try:
        report["ccx_version"] = command(
            [configuration()["ccx"], "-v"], out, out / "ccx-version.log"
        ).strip()
        report["checks"]["ccx"] = True
    except Exception as exc:
        report["checks"]["ccx"] = False
        report["ccx_error"] = str(exc)
    report["ready"] = all(report["checks"].values())
    (out / "preflight.json").write_text(json.dumps(report, indent=2))
    return report


def mesh_step(step, g, settings, out):
    import gmsh

    settings.validate()
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        if len(gmsh.model.getEntities(3)) != 1:
            raise ValueError("STEP must contain one volume")
        gmsh.option.setNumber("Mesh.MeshSizeMin", settings.size_mm * 0.45)
        gmsh.option.setNumber("Mesh.MeshSizeMax", settings.size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 0)
        gmsh.option.setNumber("General.NumThreads", 2)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("HighOrder")
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        nodes = {
            int(t): list(map(float, p))
            for t, p in zip(tags, np.asarray(xyz).reshape(-1, 3))
        }
        types, etags, connect = gmsh.model.mesh.getElements(3)
        if list(types) != [11]:
            raise ValueError("Expected Gmsh type 11 quadratic tetrahedra")
        elements = {
            int(t): list(map(int, c))
            for t, c in zip(etags[0], np.asarray(connect[0]).reshape(-1, 10))
        }
        # Gmsh edge order 01,12,20,03,23,13; CCX 01,12,20,03,13,23.
        elements = {t: c[:8] + [c[9], c[8]] for t, c in elements.items()}
        surfaces = {}
        for label, x, r in [
            ("fixed", 0, g.big_end_id / 2),
            ("loaded", g.length_cc, g.small_end_id / 2),
        ]:
            matches = []
            for _, tag in gmsh.model.getEntities(2):
                if gmsh.model.getType(2, tag) != "Cylinder":
                    continue
                center = gmsh.model.occ.getCenterOfMass(2, tag)
                area = gmsh.model.occ.getMass(2, tag)
                if (
                    abs(center[0] - x) < 1e-5
                    and abs(center[1]) < 1e-5
                    and abs(area - 2 * np.pi * r * g.beam_thickness) < 1e-4
                ):
                    matches.append(tag)
            if len(matches) != 1:
                raise ValueError(f"Ambiguous {label} bore: {matches}")
            typ, ids, con = gmsh.model.mesh.getElements(2, matches[0])
            if list(typ) != [9]:
                raise ValueError("Require six-node surface triangles")
            surfaces[label] = np.asarray(con[0]).reshape(-1, 6).astype(int).tolist()
        gmsh.write(str(Path(out) / "mesh.msh"))
        return nodes, elements, surfaces, gmsh.__version__
    finally:
        gmsh.finalize()


def surface_weights(triangles, nodes):
    # Consistent constant traction on quadratic triangles: corners have zero integral,
    # midside nodes each receive A/3. Piecewise planar approximation to the cylindrical face.
    weights = {}
    for tri in triangles:
        a, b, c = (np.asarray(nodes[n]) for n in tri[:3])
        area = float(np.linalg.norm(np.cross(b - a, c - a)) / 2)
        for n in tri[3:]:
            weights[n] = weights.get(n, 0.0) + area / 3
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Empty bore load area")
    return {k: v / total for k, v in weights.items()}


def write_input(path, nodes, elements, fixed, weights, material, load):
    material.validate()
    load.validate()
    lines = [
        "*HEADING",
        "Validated conrod: mm N MPa; distributed bore traction",
        "*NODE,NSET=ALLN",
    ]
    lines.extend(f"{n}," + ",".join(f"{v:.10e}" for v in p) for n, p in nodes.items())
    lines.append("*ELEMENT,TYPE=C3D10,ELSET=ALLE")
    lines.extend(f"{e}," + ",".join(map(str, c)) for e, c in elements.items())
    lines += [
        "*MATERIAL,NAME=ROD",
        "*ELASTIC",
        f"{material.youngs_modulus_mpa:.15g},{material.poissons_ratio:.15g}",
        "*SOLID SECTION,ELSET=ALLE,MATERIAL=ROD",
        "*BOUNDARY",
    ]
    lines.extend(f"{n},1,3" for n in sorted(fixed))
    lines += ["*STEP", "*STATIC", "*CLOAD"]
    forces = {n: load.signed_force * w for n, w in weights.items()}
    lines.extend(f"{n},1,{f:.15g}" for n, f in forces.items())
    lines += [
        "*NODE FILE",
        "U",
        "*EL FILE",
        "S",
        "*NODE PRINT,NSET=ALLN",
        "U",
        "*EL PRINT,ELSET=ALLE",
        "S",
        "*END STEP",
    ]
    Path(path).write_text("\n".join(lines) + "\n")
    return dict(
        resultant_n=[sum(forces.values()), 0.0, 0.0],
        fixed_node_count=len(fixed),
        loaded_node_count=len(forces),
        model="All big-bore translations fixed; uniform axial traction over full small bore",
        limitations="Academic clamp/traction model; not pin contact. Full bore permits tensile traction.",
    )


def von_mises(stress):
    s = np.asarray(stress, dtype=float)
    xx, yy, zz, xy, xz, yz = np.moveaxis(s, -1, 0)
    return np.sqrt(
        0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2)
        + 3 * (xy**2 + xz**2 + yz**2)
    )


def parse_dat(path):
    displacement = {}
    stress = []
    state = None
    for line in Path(path).read_text(errors="replace").splitlines():
        low = line.lower().strip()
        if low.startswith("displacements"):
            state = "u"
            continue
        if low.startswith("stresses"):
            state = "s"
            continue
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        try:
            if state == "u" and len(parts) == 4:
                displacement[int(parts[0])] = [
                    float(v.replace("D", "E")) for v in parts[1:]
                ]
            if state == "s" and len(parts) == 8:
                stress.append(
                    [int(parts[0]), int(parts[1])]
                    + [float(v.replace("D", "E")) for v in parts[2:]]
                )
        except ValueError:
            continue
    if not displacement or not stress:
        raise ValueError(
            "Missing actual displacement or integration-point stress output"
        )
    values = np.asarray(stress)[:, 2:]
    if (
        not np.isfinite(values).all()
        or not np.isfinite(list(displacement.values())).all()
    ):
        raise ValueError("Nonfinite solver fields")
    return displacement, stress


def solve(
    g: Geometry,
    m: Material,
    load: LoadCase,
    settings: MeshSettings = MeshSettings(),
    out=None,
    mode=Mode.FEA,
) -> FEAResult | AnalyticalResult:
    g.validate()
    m.validate()
    load.validate()
    settings.validate()
    mode = Mode(mode)
    if mode == Mode.ANALYTICAL:
        from .analytical import evaluate

        return evaluate(g, m, load)
    request = dict(
        geometry=g.to_dict(),
        material=m.to_dict(),
        load=load.to_dict(),
        mesh=settings.to_dict(),
        geometry_version=GEOMETRY_VERSION,
        mode=mode.value,
    )
    sid = fingerprint(request)[:20]
    out = Path(out or ROOT / "runs" / sid).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "request.json").write_text(json.dumps(request, indent=2))
    start = time.perf_counter()
    base = dict(
        sample_id=sid,
        **request,
        mesh_configuration=dict(
            size_min_mm=0.45 * settings.size_mm,
            size_max_mm=settings.size_mm,
            curvature_points=12,
            quadratic_curved=True,
            high_order_optimization=True,
            threads=2,
        ),
        solver_configuration=dict(analysis="linear static", threads=2, timeout_s=600),
        output_dir=str(out),
        data_source="FreeCAD/Gmsh/CalculiX",
        timestamp=__import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
    )
    try:
        meta = cad(g, out)
        base.update(cad=meta, mass_kg=mass_from_volume(meta["volume_mm3"], m))
        if mode == Mode.CAD_ONLY:
            result = dict(base, status="CAD_SUCCESS")
        else:
            cfg = configuration()
            if not cfg["ccx"]:
                raise RuntimeError("CalculiX unavailable")
            nodes, elements, surfaces, version = mesh_step(
                out / "geometry.step", g, settings, out
            )
            fixed = {n for t in surfaces["fixed"] for n in t}
            weights = surface_weights(surfaces["loaded"], nodes)
            boundary = write_input(
                out / "job.inp", nodes, elements, fixed, weights, m, load
            )
            if (
                abs(boundary["resultant_n"][0] - load.signed_force)
                > 1e-7 * load.force_n
            ):
                raise ValueError("Incorrect resultant")
            solver_version = command(
                [cfg["ccx"], "-v"], out, out / "solver-version.log"
            ).strip()
            log = command(
                [cfg["ccx"], "-i", "job"], out, out / "solver.log", timeout=600
            )
            if "Job finished" not in log or "*ERROR" in log.upper():
                raise RuntimeError("Solver completion marker missing or error reported")
            u, s = parse_dat(out / "job.dat")
            if len(u) != len(nodes) or set(int(row[0]) for row in s) != set(elements):
                raise ValueError("Incomplete solver field coverage")
            vm = von_mises(np.asarray(s)[:, 2:])
            disp = np.linalg.norm(list(u.values()), axis=1)
            if vm.max() <= 0 or disp.max() <= 0:
                raise ValueError("Zero response for nonzero loading")
            fields = dict(
                nodes=nodes,
                elements=elements,
                displacement=u,
                integration_point_stress=s,
                stress_components=["xx", "yy", "zz", "xy", "xz", "yz"],
            )
            (out / "fields.json").write_text(json.dumps(fields))
            result = dict(
                base,
                status="FEA_SUCCESS",
                max_von_mises_mpa=float(vm.max()),
                max_displacement_mm=float(disp.max()),
                factor_of_safety=m.yield_strength_mpa / float(vm.max()),
                node_count=len(nodes),
                element_count=len(elements),
                boundary_conditions=boundary,
                gmsh_version=version,
                solver_version=solver_version,
                fields_path=str(out / "fields.json"),
                stress_measure="Maximum unaveraged integration-point von Mises; singularity-sensitive",
            )
    except Exception as exc:
        result = dict(
            base,
            status="FEA_FAILED" if mode == Mode.FEA else "CAD_FAILED",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
    result["runtime_s"] = time.perf_counter() - start
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    return result
