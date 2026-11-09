import argparse
import json
from conrod.dataset import generate

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="data/phase2/coarse")
    p.add_argument("--geometries", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--mesh-size", type=float, default=5)
    p.add_argument("--vary-packaging", action="store_true")
    a = p.parse_args()
    print(
        json.dumps(
            generate(a.output, a.geometries, a.seed, a.mesh_size, not a.vary_packaging),
            indent=2,
        )
    )
