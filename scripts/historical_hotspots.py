import argparse
import json
from pathlib import Path
from conrod.fea import ROOT
from conrod.fields import hotspot
from conrod.schemas import Geometry

p = argparse.ArgumentParser()
p.add_argument("phase1_root")
a = p.parse_args()
source = Path(a.phase1_root)
rows = []
for directory in ["runs/refinement-final", "runs/optimization-guarded"]:
    for file in (source / directory).rglob("result.json"):
        r = json.loads(file.read_text())
        field = file.parent / "fields.json"
        if r.get("status") != "FEA_SUCCESS" or not field.exists():
            continue
        f = json.loads(field.read_text())
        g = Geometry(**r["geometry"])
        h = hotspot(f["nodes"], f["elements"], f["integration_point_stress"], g)
        rows.append(
            dict(
                source=file.relative_to(source).as_posix(),
                geometry_version=r["geometry_version"],
                load=r["load"],
                mesh=r["mesh"],
                max_von_mises_mpa=r["max_von_mises_mpa"],
                hotspot=h,
            )
        )
out = ROOT / "runs/historical-hotspots"
out.mkdir(exist_ok=True)
(out / "report.json").write_text(json.dumps(rows, indent=2))
print(f"Reconstructed {len(rows)} historical hotspots; original files unchanged")
