import json
import subprocess
import time
import threading
import queue
from pathlib import Path
from dataclasses import replace
import numpy as np
from scipy.optimize import minimize, differential_evolution
from .schemas import (
    Geometry,
    Constraints,
    MeshSettings,
    OPT_KEYS,
    BOUNDS,
    OptimizationResult,
)
from .fea import ROOT, configuration, solve
from .analytical import evaluate
from .materials import mass_from_volume


class CADMass:
    """Persistent isolated CAD interpreter; exact-key cache, no dimensional rounding."""

    def __init__(self, material):
        self.material = material
        self.cache = {}
        self.messages = queue.Queue()
        self.process = subprocess.Popen(
            [configuration()["freecad_python"], str(ROOT / "workers/volume_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def reader():
            for line in self.process.stdout:
                if line.startswith("RESULT "):
                    self.messages.put(json.loads(line[7:]))
            self.messages.put({"error": "CAD worker exited"})

        threading.Thread(target=reader, daemon=True).start()

    def __call__(self, g):
        key = tuple(g.to_dict().values())
        if key not in self.cache:
            g.validate()
            self.process.stdin.write(json.dumps(g.to_dict()) + "\n")
            self.process.stdin.flush()
            result = self.messages.get(timeout=90)
            if "error" in result:
                raise ValueError(result["error"])
            self.cache[key] = mass_from_volume(result["volume_mm3"], self.material)
        return self.cache[key]

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


def compliance(g, m, loads, results, constraints):
    reasons = []
    margins = {}
    if len(results) != len(loads):
        return False, ["Missing load-case verification"], {}
    for load, result in zip(loads, results):
        k = load.kind
        if result.get("status") != "FEA_SUCCESS":
            reasons.append(k + ": FEA failed")
            continue
        values = [
            result.get("max_von_mises_mpa", float("nan")),
            result.get("max_displacement_mm", float("nan")),
        ]
        if not all(np.isfinite(v) and v > 0 for v in values):
            reasons.append(k + ": invalid response")
            continue
        margins[k + "_stress_mpa"] = (
            m.yield_strength_mpa / constraints.min_fos - values[0]
        )
        margins[k + "_displacement_mm"] = constraints.max_displacement_mm - values[1]
        if load.kind == "compression":
            margins[k + "_buckling"] = (
                evaluate(g, m, load)["buckling_margin"]
                - constraints.min_buckling_margin
            )
    reasons += [key + " violated" for key, value in margins.items() if value < -1e-8]
    return not reasons, reasons, margins


def optimize(
    g,
    m,
    loads,
    surrogate,
    output,
    constraints=Constraints(),
    mesh=MeshSettings(),
    starts=5,
    seed=42,
    mass_function=None,
    solver=solve,
    stress_guard_factor=1.2,
    global_search=True,
) -> OptimizationResult:
    g.validate()
    m.validate()
    constraints.validate()
    mesh.validate()
    if not np.isfinite(stress_guard_factor) or stress_guard_factor < 1:
        raise ValueError("Stress guard factor must be >=1")
    if {load_case.kind for load_case in loads} != {"compression", "tension"} or len(
        loads
    ) != 2:
        raise ValueError("Require both distinct load cases")
    for load in loads:
        load.validate()
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    if hasattr(surrogate, "metadata"):
        metadata = surrogate.metadata
        if (
            metadata.get("mesh_configuration", {}).get("boundary_mode")
            != mesh.boundary_mode
        ):
            raise ValueError("Surrogate and verification boundary conditions differ")
        if (
            metadata.get("model_version", "").startswith("fea-3-")
            and metadata.get("mesh_configuration") != mesh.to_dict()
        ):
            raise ValueError("Phase 3 surrogate and verification mesh differ")
        if (
            metadata.get("model_version", "").startswith("fea-3-")
            and metadata.get("model_use") != "ACCEPTED_FOR_OPTIMIZATION"
        ):
            raise ValueError(
                "Phase 3 surrogate is exploratory only; held-out evidence does not authorize optimization"
            )
    own_mass = mass_function is None
    mass = mass_function or CADMass(m)
    diagnostics = []
    verified = []
    final = None
    lo = np.array([BOUNDS[k][0] for k in OPT_KEYS])
    hi = np.array([BOUNDS[k][1] for k in OPT_KEYS])
    # Restrict optimizer to measured feature envelope, including fixed packaging and material/load.
    if hasattr(surrogate, "metadata"):
        md = surrogate.metadata
        for i, k in enumerate(OPT_KEYS):
            j = md["features"].index(k)
            lo[i] = max(lo[i], md["supported_min"][j])
            hi[i] = min(hi[i], md["supported_max"][j])
        margin = np.array(md["residual_margin"])
    else:
        margin = np.zeros(2)

    def geometry(z):
        return replace(g, **dict(zip(OPT_KEYS, lo + np.array(z) * (hi - lo))))

    def cons(z):
        candidate = geometry(z)
        raw = [(candidate.web_thickness - 3.5) / 10, (candidate.pocket_width - 4) / 10]
        try:
            candidate.validate()
            for load in loads:
                p = surrogate.predict(candidate, m, load)
                raw += [
                    1
                    - stress_guard_factor
                    * (p["max_von_mises_mpa"] + margin[0])
                    / (m.yield_strength_mpa / constraints.min_fos),
                    1
                    - (p["max_displacement_mm"] + margin[1])
                    / constraints.max_displacement_mm,
                ]
                if load.kind == "compression":
                    raw += [
                        evaluate(candidate, m, load)["buckling_margin"]
                        / constraints.min_buckling_margin
                        - 1
                    ]
        except ValueError:
            return np.array(raw + [-1.0] * (2 * len(loads) + 1))
        return np.array(raw)

    try:
        if np.any(hi <= lo):
            raise ValueError("Empty supported optimization domain")
        # Fail early with a useful out-of-domain message for fixed inputs.
        for load in loads:
            surrogate.predict(geometry(np.full(len(OPT_KEYS), 0.5)), m, load)
        baseline = mass(g)
        rng = np.random.default_rng(seed)
        seeds = []
        for z in [
            np.clip(
                (np.array([getattr(g, k) for k in OPT_KEYS]) - lo) / (hi - lo), 0, 1
            ),
            *[rng.uniform(0, 1, len(OPT_KEYS)) for _ in range(300)],
        ]:
            if np.all(cons(z) >= 0):
                seeds.append(z)
            if len(seeds) >= starts:
                break
        if not seeds:
            trial = [rng.uniform(0, 1, len(OPT_KEYS)) for _ in range(100)]
            seeds = sorted(
                trial, key=lambda z: float(np.sum(np.minimum(cons(z), 0) ** 2))
            )[:starts]
        global_record = None
        if global_search:

            def global_objective(z):
                margins = cons(z)
                violation = np.minimum(margins, 0)
                try:
                    value = mass(geometry(z)) / baseline
                except (ValueError, RuntimeError):
                    value = 10.0
                return value + 1e3 * float(violation @ violation)

            de = differential_evolution(
                global_objective,
                [(0.0, 1.0)] * len(OPT_KEYS),
                seed=seed,
                maxiter=max(3, min(8, starts + 2)),
                popsize=5,
                tol=0.01,
                polish=False,
                workers=1,
                updating="immediate",
                init="latinhypercube",
            )
            z = np.asarray(de.x, dtype=float)
            global_record = dict(
                method="Differential Evolution",
                success=bool(de.success),
                message=str(de.message),
                evaluations=int(de.nfev),
                objective=float(de.fun),
                scaled_margins=cons(z).tolist(),
                geometry=geometry(z).to_dict(),
                seed=seed,
            )
            if np.all(cons(z) >= 0):
                seeds.insert(0, z)
            print(
                f"Differential Evolution: {de.message}; evaluations={de.nfev}",
                flush=True,
            )
        for start_index, z in enumerate(
            seeds[: max(starts, len(seeds) if not global_search else starts + 1)]
        ):
            print(f"Optimization start {start_index + 1}/{len(seeds)}", flush=True)

            def objective(z):
                try:
                    return mass(geometry(z)) / baseline
                except ValueError:
                    return 10.0 + sum(np.maximum(-cons(z), 0))

            result = minimize(
                objective,
                z,
                method="SLSQP",
                bounds=[(0.0, 1.0)] * len(OPT_KEYS),
                constraints=[dict(type="ineq", fun=cons)],
                options=dict(maxiter=60, ftol=1e-7, eps=1e-5),
            )
            margins = cons(result.x)
            print(f"SLSQP: {result.message}; iterations={result.nit}", flush=True)
            diagnostics.append(
                dict(
                    success=bool(result.success),
                    message=str(result.message),
                    iterations=int(result.nit),
                    objective=float(result.fun),
                    scaled_margins=margins.tolist(),
                    x=geometry(result.x).to_dict(),
                )
            )
        candidates = sorted(
            [
                d
                for d in diagnostics
                if d["success"] and min(d["scaled_margins"]) >= -1e-7
            ],
            key=lambda d: d["objective"],
        )
        # Bounded budget: at most three candidates, two solver cases each.
        for i, d in enumerate(candidates[:3]):
            candidate = Geometry(**d["x"])
            predictions = [
                surrogate.predict(candidate, m, load_case) for load_case in loads
            ]
            results = [
                solver(
                    candidate,
                    m,
                    load_case,
                    mesh,
                    out / f"candidate-{i}-{load_case.kind}",
                )
                for load_case in loads
            ]
            safe, reasons, margins = compliance(
                candidate, m, loads, results, constraints
            )
            verified.append(
                dict(
                    geometry=candidate.to_dict(),
                    predictions=predictions,
                    fea=results,
                    compliant=safe,
                    reasons=reasons,
                    margins=margins,
                )
            )
            if safe:
                final = verified[-1]
                break
        status = (
            "PROVISIONAL_FEA_PASS_NOT_QUALIFIED"
            if final
            else "NO_VERIFIED_FEASIBLE_DESIGN"
        )
        baseline_results = (
            [
                solver(g, m, load_case, mesh, out / f"baseline-{load_case.kind}")
                for load_case in loads
            ]
            if final
            else []
        )
        report = dict(
            status=status,
            mechanically_qualified=False,
            convergence_status="INSUFFICIENT COMPUTE / VALIDATION",
            stress_guard_claim="1.2 heuristic, not calibrated confidence; observed validation residual added separately",
            mesh_qualification="Constraint pass at specified mesh only; peak-stress convergence requires a separate study",
            baseline_geometry=g.to_dict(),
            baseline_mass_kg=baseline,
            baseline_fea=baseline_results,
            constraints=constraints.__dict__,
            stress_guard_factor=stress_guard_factor,
            material=m.to_dict(),
            loads=[load_case.to_dict() for load_case in loads],
            diagnostics=diagnostics,
            verification_attempts=verified,
            result=final,
            optimization_runtime_s=time.perf_counter() - start,
            seed=seed,
            rounding="None: full precision exported; manufacturing rounding requires reverification",
            global_search=global_record,
        )
        if final:
            report["optimized_mass_kg"] = final["fea"][0]["mass_kg"]
            report["mass_reduction_pct"] = (
                100 * (baseline - report["optimized_mass_kg"]) / baseline
            )
            report["prediction_error"] = [
                {k: r[k] - p[k] for k in ("max_von_mises_mpa", "max_displacement_mm")}
                for p, r in zip(final["predictions"], final["fea"])
            ]
    except Exception as exc:
        report = dict(
            status="OPTIMIZATION_FAILED",
            error=str(exc),
            diagnostics=diagnostics,
            verification_attempts=verified,
        )
    finally:
        if own_mass:
            mass.close()
    (out / "optimization.json").write_text(
        json.dumps(report, indent=2, allow_nan=False)
    )
    return report
