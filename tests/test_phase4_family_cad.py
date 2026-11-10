import pytest

from conrod.design_families import FAMILIES, FamilyDesign
from conrod.fea import cad, configuration


@pytest.mark.integration
@pytest.mark.parametrize("family", FAMILIES)
def test_phase4_family_exports_valid_single_solid_with_preserved_bores(family, tmp_path):
    cfg = configuration()
    if not cfg.get("freecad_python") or not cfg.get("ccx"):
        pytest.skip("Portable FreeCAD/CalculiX paths are not configured")
    design = FamilyDesign(family=family).validate()
    meta = cad(design, tmp_path / family)
    assert meta["status"] == "CAD_SUCCESS"
    assert meta["valid_topology"] is True
    assert meta["solid_count"] == 1
    assert meta["volume_mm3"] > 0
    assert len(meta["bores"]) == 2
    assert {round(b["diameter_mm"], 6) for b in meta["bores"]} == {24.0, 50.0}
    assert {round(b["center_x_mm"], 6) for b in meta["bores"]} == {0.0, 145.0}
    assert meta["transition_edges_filleted"] > 0
    for filename in ("geometry.step", "geometry.brep", "geometry.stl", "geometry.FCStd"):
        assert (tmp_path / family / filename).is_file()


@pytest.mark.integration
def test_phase4_family_actual_fea_coarse_screen(tmp_path):
    from conrod.fea import solve
    from conrod.materials import MATERIALS
    from conrod.schemas import LoadCase, MeshSettings, Mode

    cfg = configuration()
    if not cfg.get("freecad_python") or not cfg.get("ccx"):
        pytest.skip("Portable FreeCAD/CalculiX paths are not configured")
    result = solve(
        FamilyDesign(family="h_section"),
        MATERIALS["Forged Steel (AISI 4340)"],
        LoadCase("compression", 28000),
        MeshSettings(size_mm=6, local_refinement=False),
        tmp_path / "h-section-compression",
        Mode.FEA,
    )
    assert result["status"] == "FEA_SUCCESS"
    assert result["max_von_mises_mpa"] > 0
    assert result["max_displacement_mm"] > 0
    assert result["node_count"] > 0
    assert result["element_count"] > 0
