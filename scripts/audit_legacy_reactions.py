"""Re-run unchanged legacy decks with RF output; preserve original results."""

import json
import numpy as np
from conrod.fea import ROOT, configuration, command, parse_dat, von_mises
from conrod.bearing import equilibrium_audit

rows = []
for kind in ["compression", "tension"]:
    out = ROOT / "runs/phase2-experiments" / f"LEGACY_CLAMPED_BORE-4.0-{kind}"
    result = json.loads((out / "result.json").read_text())
    source = (out / "job.inp").read_text()
    deck = source.replace(
        "*EL PRINT,ELSET=ALLE", "*NODE PRINT,NSET=ALLN\nRF\n*EL PRINT,ELSET=ALLE"
    )
    (out / "reaction-audit.inp").write_text(deck)
    command(
        [configuration()["ccx"], "-i", "reaction-audit"],
        out,
        out / "reaction-audit.log",
        timeout=600,
    )
    nodes = {}
    gauges = []
    state = None
    for line in source.splitlines():
        if line.startswith("*"):
            state = (
                "nodes"
                if line.startswith("*NODE,")
                else "bc"
                if line == "*BOUNDARY"
                else None
            )
            continue
        v = line.split(",")
        if state == "nodes":
            nodes[int(v[0])] = list(map(float, v[1:]))
        if state == "bc":
            gauges.extend((int(v[0]), d) for d in range(int(v[1]), int(v[2]) + 1))
    audit = equilibrium_audit(
        out / "reaction-audit.inp",
        out / "reaction-audit.dat",
        nodes,
        gauges,
        result["load"]["force_n"],
    )
    u, s = parse_dat(out / "reaction-audit.dat")
    stress = float(max(von_mises(np.asarray(s)[:, 2:])))
    if not np.isclose(stress, result["max_von_mises_mpa"], rtol=1e-7):
        raise ValueError("Output-only rerun changed stress")
    rows.append(dict(load=kind, audit=audit, unchanged_stress_mpa=stress))
    print(kind, audit["reaction_total_n"], audit["force_balance_fraction"], flush=True)
(ROOT / "evidence/phase2/legacy-reaction-audit.json").write_text(
    json.dumps(rows, indent=2)
)
