import argparse
import json
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS
from conrod.surrogate import Surrogate
from conrod.optimizer import optimize

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="models/phase3_surrogate.joblib")
    p.add_argument("--output", default="data/phase3/optimization")
    p.add_argument("--starts", type=int, default=5)
    p.add_argument("--mesh-size", type=float, default=4.0)
    p.add_argument("--hotspot-size", type=float, default=0.75)
    p.add_argument("--refinement-region", default="big_end_transition")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-global-search", action="store_true")
    a = p.parse_args()
    r = optimize(
        Geometry(),
        MATERIALS["Forged Steel (AISI 4340)"],
        [LoadCase("compression", 28000), LoadCase("tension", 18000)],
        Surrogate(a.model),
        a.output,
        mesh=MeshSettings(
            a.mesh_size,
            hotspot_size_mm=a.hotspot_size,
            refinement_region=a.refinement_region,
        ),
        starts=a.starts,
        seed=a.seed,
        global_search=not a.no_global_search,
    )
    print(json.dumps(r, indent=2))
