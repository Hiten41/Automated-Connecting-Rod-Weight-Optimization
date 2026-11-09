"""Add Gmsh element quality for each identified actual stress hotspot."""

import json

import gmsh

from conrod.fea import ROOT


def run():
    path = ROOT / "evidence/phase3/phase3-hotspot-cad-features.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        for row in rows:
            result_path = ROOT / row["case"] / "result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            gmsh.open(str(ROOT / row["case"] / "mesh.msh"))
            quality = gmsh.model.mesh.getElementQualities(
                [int(result["hotspot"]["element_id"])], "minSICN"
            )
            row["hotspot"]["element_minSICN"] = float(quality[0])
            gmsh.clear()
    finally:
        gmsh.finalize()
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(
        json.dumps(
            [
                {
                    "case": row["case"],
                    "element": row["hotspot"]["element_id"],
                    "minSICN": row["hotspot"]["element_minSICN"],
                }
                for row in rows
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
