import argparse
import json
from conrod.surrogate import train

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="data/phase2/coarse/verified.jsonl")
    p.add_argument("--output", default="models/phase2_surrogate.joblib")
    a = p.parse_args()
    print(json.dumps(train(a.dataset, a.output), indent=2))
