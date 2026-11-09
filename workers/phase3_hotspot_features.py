"""Measure Phase 3 integration-point hotspots against the actual CAD faces."""

import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Part


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ROOT / "runs/phase3-refinement" / f"{size}-{load}"
    for size in ("0.75", "0.5", "0.35")
    for load in ("compression", "tension")
] + [
    ROOT / "data/phase3/near-boundary/4/compression",
    ROOT / "data/phase3/near-boundary/4/tension",
]


def main():
    output = []
    for case in CASES:
        result_path = case / "result.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        fields_path = case / "fields.json"
        fields = json.loads(fields_path.read_text(encoding="utf-8"))
        hotspot = result["hotspot"]
        eid = str(hotspot["element_id"])
        ip = int(hotspot["integration_point"])
        row = next(
            x
            for x in fields["integration_point_stress"]
            if int(x[0]) == int(eid) and int(x[1]) == ip
        )
        corner_ids = list(map(int, fields["elements"][eid][:4]))
        corners = [fields["nodes"][str(n)] for n in corner_ids]
        edge_lengths = [
            ((corners[i][0] - corners[j][0]) ** 2
             + (corners[i][1] - corners[j][1]) ** 2
             + (corners[i][2] - corners[j][2]) ** 2)
            ** 0.5
            for i in range(4)
            for j in range(i)
        ]
        shape = Part.Shape()
        shape.read(str(case / "geometry.brep"))
        vertex = Part.Vertex(App.Vector(*hotspot["coordinates_mm"]))
        faces = []
        for index, face in enumerate(shape.Faces, 1):
            distance = vertex.distToShape(face)[0]
            surface = face.Surface
            faces.append(
                {
                    "face": index,
                    "distance_mm": distance,
                    "surface_type": type(surface).__name__,
                    "radius_mm": getattr(surface, "Radius", None),
                }
            )
        regional = json.loads((case / "regional-stress.json").read_text())
        regional_peaks = {}
        for name, value in regional["regions"].items():
            if value.get("count", 0) == 0:
                regional_peaks[name] = value
                continue
            point = Part.Vertex(App.Vector(*value["xyz_mm"]))
            nearby = []
            for index, face in enumerate(shape.Faces, 1):
                nearby.append(
                    {
                        "face": index,
                        "distance_mm": point.distToShape(face)[0],
                        "surface_type": type(face.Surface).__name__,
                        "radius_mm": getattr(face.Surface, "Radius", None),
                    }
                )
            regional_peaks[name] = {
                **value,
                "nearest_cad_faces": sorted(
                    nearby, key=lambda face: face["distance_mm"]
                )[:4],
            }
        output.append(
            {
                "case": str(case.relative_to(ROOT)).replace("\\", "/"),
                "sample_id": result["sample_id"],
                "load": result["load"],
                "mesh": result["mesh"],
                "maximum_unaveraged_ip_von_mises_mpa": result[
                    "max_von_mises_mpa"
                ],
                "hotspot": {
                    **hotspot,
                    "components_mpa": list(map(float, row[2:])),
                    "corner_edge_lengths_mm": edge_lengths,
                    "nearest_cad_faces": sorted(
                        faces, key=lambda f: f["distance_mm"]
                    )[:4],
                },
                "regional_peaks": regional_peaks,
                "mesh_quality": json.loads(
                    (case / "mesh-quality.json").read_text(encoding="utf-8")
                ),
                "fields_sha256": hashlib.sha256(fields_path.read_bytes()).hexdigest(),
                "dat_sha256": hashlib.sha256((case / "job.dat").read_bytes()).hexdigest(),
            }
        )
    out = ROOT / "evidence/phase3/phase3-hotspot-cad-features.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        json.dumps(
            [
                {
                    "case": row["case"],
                    "hotspot": row["hotspot"]["coordinates_mm"],
                    "element": row["hotspot"]["element_id"],
                    "ip": row["hotspot"]["integration_point"],
                    "nearest_face": row["hotspot"]["nearest_cad_faces"][0],
                }
                for row in output
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
