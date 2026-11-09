"""Curved frictionless pin/ring benchmark, NOT a complete connecting rod.

Rigid hollow pin radius9.99 translates0.02mm inside radius10 bore; ring outer
radius14 fixed, thickness1, plane strain. Clearance0.01mm. Test contact
opening and angular/penalty sensitivity before any proposed rod integration.
"""

import json
import math
import numpy as np
from conrod.fea import ROOT, configuration, command


def deck(n, k):
    nodes = {}
    elements = []
    pin = []
    outer = []
    ring = []
    master = []
    slave = []
    for body, (r0, r1) in enumerate([(8, 9.99), (10, 14)]):
        lookup = {}
        for z in range(2):
            for radial in range(4):
                radius = r0 + (r1 - r0) * radial / 3
                for j in range(n):
                    tag = len(nodes) + 1
                    lookup[radial, j, z] = tag
                    angle = 2 * math.pi * j / n
                    nodes[tag] = (radius * math.cos(angle), radius * math.sin(angle), z)
                    if body == 0:
                        pin.append(tag)
                    else:
                        ring.append(tag)
                        if radial == 3:
                            outer.append(tag)
        for radial in range(3):
            for j in range(n):
                jp = (j + 1) % n
                con = [
                    lookup[r, a, z]
                    for z in (0, 1)
                    for r, a in [
                        (radial, j),
                        (radial + 1, j),
                        (radial + 1, jp),
                        (radial, jp),
                    ]
                ]
                tag = len(elements) + 1
                elements.append(con)
                if body == 0 and radial == 2:
                    slave.append(tag)
                if body == 1 and radial == 0:
                    master.append(tag)
    lines = ["*NODE"] + [
        f"{i}," + ",".join(f"{v:.12g}" for v in p) for i, p in nodes.items()
    ]
    lines += ["*ELEMENT,TYPE=C3D8,ELSET=SOLID"] + [
        f"{i}," + ",".join(map(str, c)) for i, c in enumerate(elements, 1)
    ]
    for name, ids in [("PIN", pin), ("OUTER", outer), ("RING", ring)]:
        lines += ["*NSET,NSET=" + name] + [str(i) for i in ids]
    lines += ["*SURFACE,NAME=BORE,TYPE=ELEMENT"] + [f"{i},S6" for i in master]
    lines += ["*SURFACE,NAME=PIN_SURFACE,TYPE=ELEMENT"] + [f"{i},S4" for i in slave]
    lines += [
        "*MATERIAL,NAME=STEEL",
        "*ELASTIC",
        "205000,0.29",
        "*SOLID SECTION,ELSET=SOLID,MATERIAL=STEEL",
        "*SURFACE INTERACTION,NAME=SI",
        "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
        str(k),
        "*CONTACT PAIR,INTERACTION=SI,TYPE=SURFACE TO SURFACE",
        "PIN_SURFACE,BORE",
        "*BOUNDARY",
        "OUTER,1,3",
        "RING,3,3",
        "PIN,2,3",
        "*STEP,NLGEOM,INC=200",
        "*STATIC",
        "0.05,1,1e-6,0.1",
        "*BOUNDARY",
        "PIN,1,1,0.02",
        "*NODE PRINT,NSET=PIN",
        "U,RF",
        "*NODE PRINT,NSET=OUTER",
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
    root = ROOT / "runs/phase3-pin-benchmark"
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, k in [(32, 1e6), (64, 1e6), (96, 1e6), (96, 1e7)]:
        out = root / f"n{n}-k{k:g}"
        out.mkdir(exist_ok=True)
        (out / "job.inp").write_text(deck(n, k), encoding="utf-8")
        row = dict(angular_elements=n, penalty=k)
        try:
            log = command(
                [configuration()["ccx"], "-i", "job"],
                out,
                out / "solver.log",
                timeout=120,
            )
            if "*ERROR" in log.upper() or "Job finished" not in log:
                raise ValueError("Solver did not complete")
            blocks = {}
            state = None
            for line in (out / "job.dat").read_text(encoding="utf-8").splitlines():
                s = line.strip()
                v = s.split()
                if s.startswith("forces "):
                    state = "pin" if "set PIN " in s else "outer"
                    blocks[state] = []
                elif s.startswith("contact stress "):
                    state = "pressure"
                    blocks[state] = []
                elif s.startswith("relative contact displacement "):
                    state = "gap"
                    blocks[state] = []
                elif s.startswith("displacements "):
                    state = None
                if state and v and v[0].isdigit():
                    blocks[state].append([float(x) for x in v])
            pin = np.asarray(blocks["pin"])[:, 1:].sum(axis=0)
            outer = np.asarray(blocks["outer"])[:, 1:].sum(axis=0)
            pressure = np.asarray(blocks["pressure"])[:, 2]
            row.update(
                status="COMPLETED_UNQUALIFIED_PIN_BENCHMARK",
                pin_force_n=pin.tolist(),
                outer_force_n=outer.tolist(),
                equilibrium_fraction=float(
                    np.linalg.norm(pin + outer) / np.linalg.norm(pin)
                ),
                peak_contact_pressure_mpa=float(pressure.max()),
                active_contact_samples=int(np.sum(pressure > 0)),
            )
        except Exception as exc:
            row.update(status="FAILED", error=str(exc))
        rows.append(row)
        print(row, flush=True)
        (root / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run()
