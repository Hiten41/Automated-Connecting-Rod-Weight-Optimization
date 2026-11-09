import json
import numpy as np
import pytest
from conrod import fea
from conrod.schemas import LoadCase, MeshSettings


def test_no_fallback(monkeypatch, g, m, load, tmp_path):
    def fail(*a, **kw):
        raise RuntimeError("missing solver")

    monkeypatch.setattr(fea, "cad", fail)
    r = fea.solve(g, m, load, out=tmp_path)
    assert r["status"] == "FEA_FAILED"
    assert "max_von_mises_mpa" not in r
    assert "missing solver" in r["error"]
    assert (tmp_path / "result.json").exists()


def test_missing_fields_rejected(tmp_path):
    p = tmp_path / "empty.dat"
    p.write_text("Job finished")
    with pytest.raises(ValueError):
        fea.parse_dat(p)


def test_von_mises():
    assert fea.von_mises([10, 0, 0, 0, 0, 0]) == pytest.approx(10)
    assert fea.von_mises([10, 10, 10, 0, 0, 0]) == 0
    assert fea.von_mises([0, 0, 0, 10, 0, 0]) == pytest.approx(10 * np.sqrt(3))


def test_load_resultant_and_input_field_width(m, tmp_path):
    nodes = {
        1: [-1.84741111297626e-13, 0, 0],
        2: [1, 0, 0],
        3: [0, 1, 0],
        4: [0.5, 0, 0],
        5: [0.5, 0.5, 0],
        6: [0, 0.5, 0],
    }
    w = fea.surface_weights([[1, 2, 3, 4, 5, 6]], nodes)
    assert sum(w.values()) == pytest.approx(1)
    r = fea.write_input(
        tmp_path / "test.inp", nodes, {}, [1], w, m, LoadCase("compression", 28000)
    )
    assert r["resultant_n"][0] == pytest.approx(-28000)
    text = (tmp_path / "test.inp").read_text()
    assert all(
        len(field) <= 20 for line in text.splitlines()[3:9] for field in line.split(",")
    )
    assert "-1.8474111130e-13" in text


@pytest.mark.integration
def test_real_solver_load_scaling(g, m, tmp_path):
    if not fea.configuration()["freecad_python"] or not fea.configuration()["ccx"]:
        pytest.skip("Solver unavailable; not verified")
    a = fea.solve(g, m, LoadCase("tension", 14000), MeshSettings(6), tmp_path / "a")
    assert a["status"] == "FEA_SUCCESS"
    # Reuse precisely the same mesh to isolate load scaling from mesher variability.
    inp = (tmp_path / "a/job.inp").read_text().splitlines()
    active = False
    scaled = []
    for line in inp:
        if line.startswith("*"):
            active = line == "*CLOAD"
            scaled.append(line)
            continue
        if active:
            n, dof, f = line.split(",")
            line = f"{n},{dof},{2 * float(f):.12e}"
        scaled.append(line)
    (tmp_path / "a/scaled.inp").write_text("\n".join(scaled) + "\n")
    fea.command(
        [fea.configuration()["ccx"], "-i", "scaled"],
        tmp_path / "a",
        tmp_path / "a/scaled.log",
    )
    u, s = fea.parse_dat(tmp_path / "a/scaled.dat")
    assert max(fea.von_mises(np.array(s)[:, 2:])) == pytest.approx(
        a["max_von_mises_mpa"] * 2, rel=1e-5
    )
    assert max(np.linalg.norm(v) for v in u.values()) == pytest.approx(
        a["max_displacement_mm"] * 2, rel=1e-5
    )
    assert (
        len(
            json.loads((tmp_path / "a/fields.json").read_text())[
                "integration_point_stress"
            ]
        )
        > 0
    )


def test_timeout_preserves_log(monkeypatch, tmp_path):
    import subprocess

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("ccx", 1, output=b"partial diagnostic")

    monkeypatch.setattr(fea.subprocess, "run", timeout)
    with pytest.raises(RuntimeError):
        fea.command(["ccx"], tmp_path, tmp_path / "log", timeout=1)
    assert "partial diagnostic" in (tmp_path / "log").read_text()
