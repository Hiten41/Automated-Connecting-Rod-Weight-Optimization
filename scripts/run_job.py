import json
import sys
import traceback
from pathlib import Path

from conrod.design_families import FamilyDesign
from conrod.fea import ROOT, solve
from conrod.optimizer import optimize
from conrod.schemas import Constraints, Geometry, LoadCase, Material, MeshSettings
from conrod.surrogate import Surrogate

if __name__ == "__main__":
    job = json.loads(Path(sys.argv[1]).read_text())
    out = Path(job["output"])
    try:
        geometry_data = job["geometry"]
        g = (
            FamilyDesign(**geometry_data)
            if "family" in geometry_data
            else Geometry(**geometry_data)
        )
        m = Material(**job["material"])
        loads = [LoadCase(**load_case) for load_case in job["loads"]]
        mesh = MeshSettings(**job["mesh"])
        if job["action"] == "OPTIMIZE + FEA":
            result = optimize(
                g,
                m,
                loads,
                Surrogate(ROOT / "models/phase3_surrogate.joblib"),
                out,
                Constraints(**job["constraints"]),
                mesh,
            )
        else:
            rows = [
                solve(g, m, load_case, mesh, out / load_case.kind, mode=job["action"])
                for load_case in loads
            ]
            result = {
                "status": "COMPLETED"
                if all(r["status"] in ("CAD_SUCCESS", "FEA_SUCCESS") for r in rows)
                else "FAILED",
                "geometry": g.to_dict(),
                "results": rows,
            }
    # Persist any worker failure so the UI can recover the job state after refresh.
    except Exception as exc:  # noqa: BLE001
        # A background boundary must record all dependency failures, including CAD/solver errors.
        result = {
            "status": "FAILED",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    result["load_provenance"] = job.get("load_provenance", "MANUAL")
    temp = out / "ui-result.tmp"
    temp.write_text(json.dumps(result, indent=2))
    temp.replace(out / "ui-result.json")
