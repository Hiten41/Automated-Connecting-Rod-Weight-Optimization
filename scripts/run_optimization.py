import argparse
import json
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS
from conrod.surrogate import Surrogate
from conrod.optimizer import optimize

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="models/phase2_surrogate.joblib")
    p.add_argument("--output", default="runs/phase2-optimization")
    p.add_argument("--starts", type=int, default=5)
    p.add_argument("--mesh-size", type=float, default=4.0)
    a = p.parse_args()
    r = optimize(
        Geometry(),
        next(iter(MATERIALS.values())),
        [LoadCase("compression", 28000), LoadCase("tension", 18000)],
        Surrogate(a.model),
        a.output,
        mesh=MeshSettings(a.mesh_size, hotspot_size_mm=min(1.25, a.mesh_size)),
        starts=a.starts,
    )
    print(json.dumps(r, indent=2))
