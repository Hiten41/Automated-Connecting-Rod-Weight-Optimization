from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_all_sections_render():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    for page in [
        "legacy_geometry_editor",
        "engine_loading",
        "simulation",
        "optimization_feasibility",
        "results_comparison",
        "model_analytics",
        "reports_downloads",
        "design_studio",
        "design_space_explorer",
    ]:
        app.switch_page(f"pages/{page}.py").run()
        assert not app.exception, (page, app.exception)
    app.switch_page("pages/legacy_geometry_editor.py").run()
    assert len(app.number_input) == 9


def test_phase4_family_selector_updates_without_running_solvers():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("pages/design_studio.py").run()
    family = next(item for item in app.selectbox if item.label == "Geometry family")
    family.set_value("tapered").run()
    assert not app.exception
    assert family.value == "tapered"
    assert not app.session_state.get("phase4_last_results")


def test_dashboard_presents_engineering_metrics_without_raw_json():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert not app.get("json")
    developer_panels = [
        panel for panel in app.expander if "Advanced diagnostics" in panel.label
    ]
    assert developer_panels
    assert all(not panel.proto.expanded for panel in developer_panels)
    rendered_text = "\n".join(
        [item.value for item in app.markdown if isinstance(item.value, str)]
        + [item.value for item in app.caption if isinstance(item.value, str)]
    )
    assert '"attempted_geometries"' not in rendered_text
    assert '"INFEASIBLE_ON_TESTED_MESH"' not in rendered_text
    metric_values = {metric.label: metric.value for metric in app.metric}
    assert metric_values["CAD / FEA solver status"] == "Ready"
    assert metric_values["Design attempts"] == "133"
    assert metric_values["Valid CAD solids"] == "120"
    assert metric_values["Completed FEA load-case records"] == "86"
    assert metric_values["Passing numerical screens"] == "4"


def test_results_page_formats_nested_job_results_as_engineering_summary(tmp_path):
    import json

    job_dir = ROOT / "runs/ui-phase4" / f"00-ui-regression-{tmp_path.name}"
    job_dir.mkdir(parents=True, exist_ok=True)
    result_path = job_dir / "ui-result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "load_provenance": "TEST_FIXTURE",
                "results": [
                    {
                        "status": "FEA_SUCCESS",
                        "load": {"kind": "tension", "force_n": 18000},
                        "mesh": {"size_mm": 1.0, "order": 2},
                        "cad": {"valid_topology": True, "solid_count": 1},
                        "mass_kg": 0.87,
                        "max_von_mises_mpa": 366.0,
                        "max_displacement_mm": 0.091,
                        "runtime_s": 12.5,
                        "geometry": {"length_cc": 145.0},
                        "material": {"name": "AISI 4340"},
                        "implementation_sha256": {"fea.py": "internal-hash"},
                        "solver_configuration": {"threads": 2},
                        "mesh_configuration": {"random_seed": 42},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        app.switch_page("pages/results_comparison.py").run()
        job_selector = next(
            item for item in app.selectbox if item.label == "Application job"
        )
        job_selector.set_value(result_path)
        app.run()
        assert not app.exception
        columns = [
            list(widget.value.columns)
            for widget in app.dataframe
            if hasattr(widget.value, "columns")
        ]
        result_columns = next(cols for cols in columns if "Load case" in cols)
        assert "Peak stress (MPa)" in result_columns
        assert not {
            "geometry",
            "material",
            "load",
            "mesh",
            "implementation_sha256",
            "solver_configuration",
            "mesh_configuration",
        }.intersection(result_columns)
    finally:
        result_path.unlink(missing_ok=True)
        job_dir.rmdir()


def test_reference_engine_graphs():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("pages/engine_loading.py").run()
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
    app.switch_page("pages/legacy_geometry_editor.py").run()
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
