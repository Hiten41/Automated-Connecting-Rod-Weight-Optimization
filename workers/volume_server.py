import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from conrod.schemas import Geometry
from conrod.geometry import build_connecting_rod

for line in sys.stdin:
    try:
        shape, meta = build_connecting_rod(Geometry(**json.loads(line)))
        print("RESULT " + json.dumps({"volume_mm3": meta["volume_mm3"]}), flush=True)
    except Exception as exc:
        print("RESULT " + json.dumps({"error": str(exc)}), flush=True)
