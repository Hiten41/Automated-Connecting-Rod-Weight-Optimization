"""Bounded expansion after initial pilot exposed poor surrogate quality."""

import time
from conrod.fea import ROOT
from conrod.dataset import generate
from conrod.surrogate import train, Surrogate
from conrod.optimizer import optimize
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS

start = time.monotonic()
while not (ROOT / "runs/engine-example/experiment.json").exists():
    if time.monotonic() - start > 3600:
        raise TimeoutError("Initial experiments did not complete")
    time.sleep(5)
report = generate(ROOT / "data/phase2/coarse", count=60, seed=44, size_mm=8)
print(report, flush=True)
if report["successful_analyses"] < 80:
    raise RuntimeError("Insufficient expansion data")
model = ROOT / "models/phase2_surrogate.joblib"
md = train(ROOT / "data/phase2/coarse/verified.jsonl", model, seed=42)
print("MODEL", md["selected_model"], md["held_out_metrics"], flush=True)
result = optimize(
    Geometry(),
    MATERIALS["Forged Steel (AISI 4340)"],
    [LoadCase(), LoadCase("tension", 18000)],
    Surrogate(model),
    ROOT / "runs/phase2-optimization",
    mesh=MeshSettings(4, hotspot_size_mm=1.25),
    starts=5,
)
print("OPTIMIZATION", result["status"], result.get("error"), flush=True)
