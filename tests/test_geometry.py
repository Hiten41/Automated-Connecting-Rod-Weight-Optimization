from dataclasses import replace
import pytest
import trimesh
from conrod.fea import cad, configuration


@pytest.mark.parametrize(
    "field,value",
    [
        ("length_cc", float("nan")),
        ("ring_thickness", 0),
        ("beam_thickness", float("inf")),
    ],
)
def test_invalid_bounds(g, field, value):
    with pytest.raises(ValueError):
        replace(g, **{field: value}).validate()


def test_invalid_web_not_clamped(g):
    bad = replace(g, beam_thickness=14, pocket_depth=6)
    with pytest.raises(ValueError):
        bad.validate()
    assert bad.pocket_depth == 6


def test_invalid_pocket_not_clamped(g):
    with pytest.raises(ValueError):
        replace(g, shank_width=15, flange_thickness=6).validate()


@pytest.mark.integration
def test_real_cad_and_export_consistency(g, tmp_path):
    if not configuration()["freecad_python"]:
        pytest.skip("FreeCAD unavailable; not verified")
    r = cad(g, tmp_path)
    assert r["solid_count"] == 1 and r["valid_topology"]
    assert sorted(x["diameter_mm"] for x in r["bores"]) == [24, 50]
    assert (
        max(x["center_x_mm"] for x in r["bores"])
        - min(x["center_x_mm"] for x in r["bores"])
        == 145
    )
    assert r["web_thickness_mm"] == pytest.approx(17.6)
    assert r["flange_thickness_mm"] == 5.5
    assert r["measured_web_thickness_mm"] == pytest.approx(17.6)
    assert r["measured_flange_thicknesses_mm"] == pytest.approx([5.5, 5.5])
    mesh = trimesh.load(tmp_path / "geometry.stl")
    assert mesh.is_watertight
    assert len(mesh.split()) == 1
    assert mesh.volume == pytest.approx(r["volume_mm3"], rel=0.003)
    assert (tmp_path / "geometry.step").stat().st_size > 1000
