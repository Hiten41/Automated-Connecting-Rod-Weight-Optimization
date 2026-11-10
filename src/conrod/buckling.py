"""Linear eigenvalue buckling using the existing CalculiX solid mesh.

This is an elastic bifurcation estimate. It is not nonlinear post-buckling,
imperfection-sensitive collapse, or fatigue qualification.
"""

from pathlib import Path
import re

from .fea import command, configuration


def parse_buckling_factors(dat_text):
    match = re.search(r"BUCKLING\s+FACTOR", dat_text, re.IGNORECASE)
    if not match:
        raise ValueError("CalculiX .dat has no BUCKLING FACTOR table")
    factors = []
    for line in dat_text[match.end():].splitlines()[:20]:
        values = re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][-+]?\d+)?", line)
        if len(values) >= 2:
            try:
                mode = int(values[0])
                value = float(values[-1].replace("D", "E").replace("d", "e"))
            except ValueError:
                continue
            if mode > 0 and value != 0:
                factors.append(value)
    positive = sorted(value for value in factors if value > 0)
    if not positive:
        raise ValueError("No positive buckling factor was extracted from .dat")
    return positive


def run_linear_buckling(static_input, output_dir, modes=5, timeout=600):
    """Run *BUCKLE on the saved compression mesh and bearing-force pattern.

    ``static_input`` must be an actual COSINE_BEARING compression input deck.
    The material, nodes, C3D10 elements, and six zero-valued gauge constraints
    are reused; only its static step is replaced by a proportional eigenvalue
    buckling step. No prescribed displacement is introduced as a load.
    """
    source = Path(static_input)
    lines = source.read_text(encoding="utf-8").splitlines()
    step_index = next((i for i, line in enumerate(lines) if line.strip().upper().startswith("*STEP")), None)
    if step_index is None:
        raise ValueError("Static input deck has no *STEP")
    load_index = next((i for i in range(step_index, len(lines)) if lines[i].strip().upper() == "*CLOAD"), None)
    if load_index is None:
        raise ValueError("Static input deck has no *CLOAD proportional loading")
    load_end = load_index + 1
    while load_end < len(lines) and not lines[load_end].strip().startswith("*"):
        load_end += 1
    if load_end == load_index + 1:
        raise ValueError("Static input deck has an empty *CLOAD block")
    loads = lines[load_index:load_end]
    deck = lines[:step_index] + [
        "*STEP",
        "*BUCKLE",
        f"{int(modes)},0.001,{max(4 * int(modes), 20)},1000",
        *loads,
        "*NODE FILE",
        "U",
        "*END STEP",
    ]
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    deck_path = out / "buckle.inp"
    deck_path.write_text("\n".join(deck) + "\n", encoding="utf-8")
    cfg = configuration()
    if not cfg.get("ccx"):
        raise RuntimeError("CalculiX path is not configured")
    log = command([cfg["ccx"], "-i", "buckle"], out, out / "buckle.log", timeout=timeout)
    if "Job finished" not in log or "*ERROR" in log.upper():
        raise RuntimeError("CalculiX buckling run did not complete cleanly")
    dat = (out / "buckle.dat").read_text(errors="replace")
    factors = parse_buckling_factors(dat)
    result = {
        "status": "BUCKLING_SUCCESS",
        "method": "CalculiX linear eigenvalue buckling; C3D10; proportional 28 kN COSINE_BEARING load pattern",
        "lowest_positive_factor": factors[0],
        "positive_factors": factors,
        "reference_compression_n": 28000.0,
        "linear_eigenvalue_load_n": factors[0] * 28000.0,
        "limitations": [
            "Linear bifurcation only; no geometric imperfections or nonlinear collapse",
            "COSINE_BEARING equivalent pressure and six rigid-body gauge DOFs are retained",
            "An eigenvalue below zero is not used as a positive buckling margin",
        ],
        "input_deck": str(deck_path),
        "raw_data": str(out / "buckle.dat"),
        "solver_log": str(out / "buckle.log"),
    }
    (out / "buckling.json").write_text(__import__("json").dumps(result, indent=2))
    return result
