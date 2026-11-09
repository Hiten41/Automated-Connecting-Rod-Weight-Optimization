"""Measure raw-field hotspot distances to actual OpenCascade CAD faces."""

import json
from pathlib import Path
import FreeCAD as App
import Part

root = Path(__file__).resolve().parents[1]
rows = json.loads(
    (root / "evidence/phase3/historical-field-audit.json").read_text(encoding="utf-8")
)
for row in rows:
    shape = Part.Shape()
    shape.read(
        str(
            root.parent
            / "phase2-rod/runs/focused-refinement"
            / row["case"]
            / "geometry.brep"
        )
    )
    vertex = Part.Vertex(App.Vector(*row["xyz_mm"]))
    faces = []
    for i, face in enumerate(shape.Faces, 1):
        distance = vertex.distToShape(face)[0]
        surface = face.Surface
        faces.append(
            dict(
                face=i,
                distance_mm=distance,
                surface_type=type(surface).__name__,
                radius_mm=getattr(surface, "Radius", None),
            )
        )
    row["nearest_cad_faces"] = sorted(faces, key=lambda f: f["distance_mm"])[:4]
(root / "evidence/phase3/hotspot-cad-features.json").write_text(
    json.dumps(rows, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        [{"case": r["case"], "nearest": r["nearest_cad_faces"][0]} for r in rows],
        indent=2,
    )
)
