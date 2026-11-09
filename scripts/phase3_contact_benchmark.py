"""Independent flat-interface penalty contact patch test, not pin validation.

Two 1mm cubes, E=200000MPa, nu=0, prescribed 0.002mm shortening.
Exact uniform force with penalty k: delta/(2/E+1/k) N for area=1mm2.
"""

import json
import numpy as np
from conrod.fea import ROOT, configuration, command


def audit(path, analytical):
    blocks = {}
    state = None
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text.startswith("forces "):
            state = "top" if "set TOP " in text else "bottom"
            blocks[state] = []
        elif text.startswith("contact stress "):
            state = "pressure"
            blocks[state] = []
        elif text.startswith("relative contact displacement "):
            state = "gap"
            blocks[state] = []
        elif text.startswith("displacements "):
            state = None
        values = text.split()
        if state and values and values[0].isdigit():
            blocks[state].append([float(v) for v in values])
    top = np.asarray(blocks["top"])[:, 1:].sum(axis=0)
    bottom = np.asarray(blocks["bottom"])[:, 1:].sum(axis=0)
    pressure = np.asarray(blocks["pressure"])[:, 2]
    gap = np.asarray(blocks["gap"])[:, 2]
    error = abs(abs(top[2]) - analytical) / analytical
    balance = float(np.linalg.norm(top + bottom) / analytical)
    return dict(
        top_reaction_n=top.tolist(),
        bottom_reaction_n=bottom.tolist(),
        relative_analytical_error=float(error),
        relative_equilibrium_error=balance,
        pressure_range_mpa=[float(pressure.min()), float(pressure.max())],
        signed_gap_range_mm=[float(gap.min()), float(gap.max())],
        status="PATCH_TEST_PASSED"
        if error < 0.005 and balance < 1e-6 and pressure.min() > 0
        else "PATCH_TEST_FAILED",
        limit="Uniform frictionless closed flat interface only; does not validate curved pin contact, sliding, separation or rod stress",
    )


def deck(n, k):
    nodes = {}
    elements = []
    bottom = []
    top = []
    xzero = []
    yzero = []
    masters = []
    slaves = []
    for block in range(2):
        lookup = {}
        for z in range(n + 1):
            for y in range(n + 1):
                for x in range(n + 1):
                    tag = len(nodes) + 1
                    lookup[x, y, z] = tag
                    nodes[tag] = (x / n, y / n, block + z / n)
                    if x == 0:
                        xzero.append(tag)
                    if y == 0:
                        yzero.append(tag)
                    if block == 0 and z == 0:
                        bottom.append(tag)
                    if block == 1 and z == n:
                        top.append(tag)
        for z in range(n):
            for y in range(n):
                for x in range(n):
                    con = [
                        lookup[x + i, y + j, z + l]
                        for i, j, l in [
                            (0, 0, 0),
                            (1, 0, 0),
                            (1, 1, 0),
                            (0, 1, 0),
                            (0, 0, 1),
                            (1, 0, 1),
                            (1, 1, 1),
                            (0, 1, 1),
                        ]
                    ]
                    tag = len(elements) + 1
                    elements.append(con)
                    if block == 0 and z == n - 1:
                        masters.append(tag)
                    if block == 1 and z == 0:
                        slaves.append(tag)
    lines = ["*NODE"] + [f"{i}," + ",".join(map(str, p)) for i, p in nodes.items()]
    lines += ["*ELEMENT,TYPE=C3D8,ELSET=SOLID"] + [
        f"{i}," + ",".join(map(str, c)) for i, c in enumerate(elements, 1)
    ]
    for name, ids in [
        ("BOTTOM", bottom),
        ("TOP", top),
        ("XZERO", xzero),
        ("YZERO", yzero),
    ]:
        lines += ["*NSET,NSET=" + name] + [str(i) for i in ids]
    lines += ["*SURFACE,NAME=MASTER,TYPE=ELEMENT"] + [f"{i},S2" for i in masters]
    lines += ["*SURFACE,NAME=SLAVE,TYPE=ELEMENT"] + [f"{i},S1" for i in slaves]
    lines += [
        "*MATERIAL,NAME=ELASTIC",
        "*ELASTIC",
        "200000,0",
        "*SOLID SECTION,ELSET=SOLID,MATERIAL=ELASTIC",
        "*SURFACE INTERACTION,NAME=INTERACTION",
        "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
        f"{k}",
        "*CONTACT PAIR,INTERACTION=INTERACTION,TYPE=SURFACE TO SURFACE",
        "SLAVE,MASTER",
        "*BOUNDARY",
        "BOTTOM,3,3",
        "XZERO,1,1",
        "YZERO,2,2",
        "*STEP,NLGEOM,INC=100",
        "*STATIC",
        "0.1,1,1e-6,0.2",
        "*BOUNDARY",
        "TOP,3,3,-0.002",
        "*NODE PRINT,NSET=TOP",
        "U,RF",
        "*NODE PRINT,NSET=BOTTOM",
        "U,RF",
        "*CONTACT PRINT",
        "CDIS,CSTR",
        "*NODE FILE",
        "U",
        "*EL FILE",
        "S",
        "*END STEP",
    ]
    return "\n".join(lines) + "\n"


def run():
    root = ROOT / "runs/phase3-contact-benchmark"
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, k in [(2, 1e6), (4, 1e6), (4, 1e7)]:
        out = root / f"n{n}-k{k:g}"
        out.mkdir(exist_ok=True)
        (out / "job.inp").write_text(deck(n, k), encoding="utf-8")
        try:
            log = command(
                [configuration()["ccx"], "-i", "job"],
                out,
                out / "solver.log",
                timeout=120,
            )
            status = (
                "SOLVER_COMPLETED_UNVALIDATED"
                if "Job finished" in log and "*ERROR" not in log.upper()
                else "FAILED"
            )
        except Exception as exc:
            status = "FAILED"
            log = str(exc)
        rows.append(
            dict(
                n=n,
                penalty_mpa_per_mm=k,
                status=status,
                analytical_force_n=0.002 / (2 / 200000 + 1 / k),
                note="Flat contact patch test only; reaction and contact-output audit required",
            )
        )
        if status == "SOLVER_COMPLETED_UNVALIDATED":
            rows[-1]["audit"] = audit(out / "job.dat", rows[-1]["analytical_force_n"])
        print(rows[-1], flush=True)
    (root / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run()
