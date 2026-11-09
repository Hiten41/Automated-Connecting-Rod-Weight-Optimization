import json
from conrod.fea import ROOT
from conrod.bearing import equilibrium_audit

rows = []
for directory in [
    "runs/focused-refinement",
    "runs/phase2-experiments",
    "data/phase2/coarse/cases",
    "data/phase2/fine/cases",
    "runs/phase2-optimization",
    "runs/phase2-diagnostic-verification",
    "runs/engine-example",
]:
    for file in (ROOT / directory).rglob("result.json"):
        result = json.loads(file.read_text())
        if (
            result.get("status") != "FEA_SUCCESS"
            or result["mesh"]["boundary_mode"] != "COSINE_BEARING"
        ):
            continue
        d = file.parent
        # Read actual deck nodes; avoids loading the much larger full field file.
        nodes = {}
        active = False
        for line in (d / "job.inp").read_text().splitlines():
            if line.startswith("*"):
                active = line.upper().startswith("*NODE,")
                continue
            if active:
                values = line.split(",")
                nodes[int(values[0])] = list(map(float, values[1:]))
        audit = equilibrium_audit(
            d / "job.inp",
            d / "job.dat",
            nodes,
            result["boundary_conditions"]["gauges"],
            result["load"]["force_n"],
        )
        rows.append(dict(path=file.relative_to(ROOT).as_posix(), audit=audit))
out = ROOT / "evidence/phase2/equilibrium-audit.json"
out.write_text(json.dumps(rows, indent=2))
print(
    "Audited",
    len(rows),
    "cases; worst force residual fraction",
    max((r["audit"]["force_balance_fraction"] for r in rows), default=0),
)
