"""Sequential controller; await already-running global study, then independent stages."""

import time
import subprocess
import sys
from conrod.fea import ROOT

start = time.monotonic()
while not (ROOT / "runs/phase2-experiments/convergence.json").exists():
    if time.monotonic() - start > 2400:
        raise TimeoutError("Global study did not finish; inspect its log")
    time.sleep(5)
for script in [
    "focused_refinement.py",
    "phase2_learning.py",
    "multifidelity.py",
    "engine_fea_example.py",
]:
    print("START", script, flush=True)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT
    )
    print("FINISH", script, completed.returncode, flush=True)
