import json
from conrod.dataset import generate
from conrod.surrogate import train, Surrogate
from conrod.optimizer import optimize
from conrod.fea import ROOT
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS


def run():
    out = ROOT / "data/phase2/coarse"
    pilot = generate(out, count=3, seed=42, size_mm=8)
    (out / "pilot-manifest.json").write_text(json.dumps(pilot, indent=2))
    if pilot["successful_analyses"] < 4:
        print("Pilot insufficient; stop expansion", flush=True)
        return
    report = generate(out, count=60, seed=44, size_mm=8)
    print(report, flush=True)
    if report["successful_analyses"] < 24:
        return
    model = ROOT / "models/phase2_surrogate.joblib"
    md = train(out / "verified.jsonl", model)
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


if __name__ == "__main__":
    run()
