from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_all_sections_render():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    for name in [
        "Geometry Designer",
        "Engine Loading",
        "Simulation",
        "AI Optimization",
        "Results & Comparison",
        "Model Analytics",
        "Reports & Downloads",
    ]:
        app.sidebar.radio[0].set_value(name).run()
        assert not app.exception, (name, app.exception)
    app.sidebar.radio[0].set_value("Geometry Designer").run()
    assert len(app.number_input) == 9


def test_reference_engine_graphs():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Engine Loading").run()
    next(x for x in app.radio if x.label == "Loading mode").set_value(
        "Engine-derived loading"
    ).run()
    app.selectbox[0].set_value("Published Hydra plot comparison (approximate)").run()
    app.button[0].click().run()
    assert not app.exception
    assert len(app.metric) == 2


import pytest


@pytest.mark.integration
def test_background_cad_job_snapshot_and_exports():
    import json
    from conrod.fea import configuration

    if not configuration()["freecad_python"]:
        pytest.skip("FreeCAD not configured")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Geometry Designer").run()
    next(b for b in app.button if b.label == "Generate Preview").click().run()
    assert not app.exception
    directory = Path(app.session_state["job_dir"])
    job = json.loads((directory / "job.json").read_text())
    assert len(job["geometry"]) == 9
    process = app.session_state["process"]
    process.wait(timeout=30)
    app.run()
    result = json.loads((directory / "ui-result.json").read_text())
    assert result["status"] == "COMPLETED"
    assert (directory / "compression/geometry.step").is_file()
    assert (directory / "compression/geometry.stl").is_file()
