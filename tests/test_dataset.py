import pytest
from conrod.dataset import validate_record, load_verified
from conrod.schemas import Geometry, LoadCase, MeshSettings, GEOMETRY_VERSION
from conrod.materials import MATERIALS
import json


def record():
    return dict(
        status="FEA_SUCCESS",
        data_source="FreeCAD/Gmsh/CalculiX",
        geometry=Geometry().to_dict(),
        material=next(iter(MATERIALS.values())).to_dict(),
        load=LoadCase().to_dict(),
        mesh=MeshSettings().to_dict(),
        mass_kg=0.7,
        max_von_mises_mpa=355.0,
        max_displacement_mm=0.1,
        factor_of_safety=2.0,
        node_count=100,
        element_count=20,
        solver_version="test fixture",
        geometry_version=GEOMETRY_VERSION,
        simulation_version="phase2-bearing-v1",
        fields_path="fixture",
        sample_id="one",
    )


@pytest.mark.parametrize(
    "status", ["SUCCESS_CAD_VERIFIED", "ANALYTICAL", "FEA_FAILED", "SUCCESS_CCX"]
)
def test_excludes_legacy_and_failures(status):
    r = record()
    r["status"] = status
    with pytest.raises(ValueError):
        validate_record(r)


def test_nonfinite():
    r = record()
    r["max_von_mises_mpa"] = float("nan")
    with pytest.raises(ValueError):
        validate_record(r)


def test_duplicates(tmp_path):
    p = tmp_path / "data"
    p.write_text((json.dumps(record()) + "\n") * 2)
    with pytest.raises(ValueError):
        load_verified(p)


def test_batch_lhs_stratification_and_resume(monkeypatch, tmp_path):
    from conrod import dataset
    import json

    calls = []

    def fake(g, m, load, mesh, out):
        calls.append(g)
        r = record()
        r.update(
            geometry=g.to_dict(),
            material=m.to_dict(),
            load=load.to_dict(),
            mesh=mesh.to_dict(),
            sample_id=dataset.fingerprint([g.to_dict(), load.to_dict()]),
            geometry_version=dataset.GEOMETRY_VERSION,
            simulation_version="phase3-deterministic-bearing-v1",
        )
        r["factor_of_safety"] = m.yield_strength_mpa / r["max_von_mises_mpa"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(json.dumps(r))
        return r

    monkeypatch.setattr(dataset, "solve", fake)
    report = dataset.generate(tmp_path, count=12, seed=44)
    assert report["rejected_geometry_samples"] == 0
    values = [g.ring_thickness for g in calls[::2]]
    assert len({int((v - 4.5) / 4.5 * 12) for v in values}) == 12
    dataset.generate(tmp_path, count=12, seed=44)
    assert len(calls) == 24
