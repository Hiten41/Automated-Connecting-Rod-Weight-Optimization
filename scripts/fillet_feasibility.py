import json
from dataclasses import replace
from conrod.fea import ROOT, cad
from conrod.schemas import Geometry

rows = []
for radius in [0.5, 1, 1.5, 2, 3]:
    try:
        g = replace(Geometry(), transition_radius_mm=radius).validate()
        r = cad(g, ROOT / "runs/fillet-feasibility" / str(radius))
        rows.append(
            dict(
                radius_mm=radius,
                status=r["status"],
                volume_mm3=r["volume_mm3"],
                web_mm=r["measured_web_thickness_mm"],
                bores=r["bores"],
            )
        )
    except Exception as exc:
        rows.append(dict(radius_mm=radius, status="INVALID_GEOMETRY", error=str(exc)))
(ROOT / "runs/fillet-feasibility/report.json").write_text(json.dumps(rows, indent=2))
print(rows)
