"""Diagnostic FEA of new SLSQP points; never relabel failed optimization as success."""

import json
import numpy as np
from conrod.fea import ROOT
from conrod.schemas import Geometry, LoadCase, MeshSettings, Constraints
from conrod.materials import MATERIALS
from conrod.optimizer import compliance
from phase2_experiments import run_case


def run():
    report = json.loads(
        (ROOT / "runs/phase2-optimization/optimization.json").read_text()
    )
    out = ROOT / "runs/phase2-diagnostic-verification"
    out.mkdir(exist_ok=True)
    rows = []
    seen = []
    candidates = sorted(
        report.get("diagnostics", []),
        key=lambda d: (
            float(np.sum(np.minimum(d["scaled_margins"], 0) ** 2)),
            d["objective"],
        ),
    )
    for d in candidates:
        try:
            g = Geometry(**d["x"]).validate()
        except ValueError:
            continue
        vector = np.array(list(g.to_dict().values()))
        if any(np.allclose(vector, x, atol=1e-4, rtol=0) for x in seen):
            continue
        seen.append(vector)
        m = MATERIALS["Forged Steel (AISI 4340)"]
        loads = [LoadCase(), LoadCase("tension", 18000)]
        fea = [
            run_case(
                g,
                m,
                lc,
                MeshSettings(4, hotspot_size_mm=1.25),
                out / f"candidate-{len(rows)}-{lc.kind}",
            )
            for lc in loads
        ]
        safe, reasons, margins = compliance(g, m, loads, fea, Constraints())
        rows.append(
            dict(
                geometry=g.to_dict(),
                optimizer_diagnostic=d,
                fea=fea,
                constraint_pass_at_one_mesh=safe,
                reasons=reasons,
                margins=margins,
                mechanically_qualified=False,
            )
        )
        if len(rows) >= 2:
            break
    result = dict(
        status="DIAGNOSTIC_ONLY_NOT_AN_ACCEPTED_OPTIMUM",
        reason="SLSQP/surrogate constraints did not provide an accepted candidate; independent FEA tests promising final points without hiding rejection.",
        candidates=rows,
        baseline_mass_kg=report.get("baseline_mass_kg"),
        convergence_status="INSUFFICIENT COMPUTE / VALIDATION",
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2))
    print(
        result["status"],
        [(x["constraint_pass_at_one_mesh"], x["reasons"]) for x in rows],
        flush=True,
    )
    return result


if __name__ == "__main__":
    run()
