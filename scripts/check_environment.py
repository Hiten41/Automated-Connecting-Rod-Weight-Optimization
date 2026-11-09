import json
from conrod.fea import preflight

if __name__ == "__main__":
    print(json.dumps(preflight(), indent=2))
