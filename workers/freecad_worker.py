"""Run with portable FreeCAD's bundled python.exe (not system Python)."""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from conrod.schemas import Geometry
from conrod.geometry import build_connecting_rod


def main():
    request_path = Path(sys.argv[1]).resolve()
    job = json.loads(request_path.read_text())
    out = Path(job["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    try:
        import FreeCAD
        import MeshPart

        if job.get("preflight"):
            result = dict(
                status="PREFLIGHT_SUCCESS",
                freecad_version=FreeCAD.Version(),
                python_version=sys.version,
                fem_modules=True,
            )
        else:
            shape, meta = build_connecting_rod(Geometry(**job["geometry"]))
            shape.exportStep(str(out / "geometry.step"))
            shape.exportBrep(str(out / "geometry.brep"))
            mesh = MeshPart.meshFromShape(
                Shape=shape,
                LinearDeflection=0.08,
                AngularDeflection=0.15,
                Relative=False,
            )
            mesh.write(str(out / "geometry.stl"))
            doc = FreeCAD.newDocument("Rod")
            part = doc.addObject("Part::Feature", "Rod")
            part.Shape = shape
            doc.recompute()
            doc.saveAs(str(out / "geometry.FCStd"))
            FreeCAD.closeDocument(doc.Name)
            result = dict(
                status="CAD_SUCCESS",
                **meta,
                freecad_version=FreeCAD.Version(),
                python_version=sys.version,
            )
        (out / "cad.json").write_text(json.dumps(result, indent=2))
    except Exception as exc:
        (out / "cad.json").write_text(
            json.dumps(
                dict(
                    status="CAD_FAILED",
                    error=str(exc),
                    traceback=traceback.format_exc(),
                ),
                indent=2,
            )
        )
        raise


if __name__ == "__main__":
    main()
