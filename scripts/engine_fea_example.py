import json
from dataclasses import replace
from conrod.fea import ROOT
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS
from reference_engine import run
from phase2_experiments import run_case

report = run()
peaks = report["peaks"]
rows = []
g = replace(Geometry(), length_cc=peaks["engine"]["rod_length_mm"])
for kind in ["compression", "tension"]:
    r = run_case(
        g,
        MATERIALS["Forged Steel (AISI 4340)"],
        LoadCase(kind, peaks[kind + "_n"]),
        MeshSettings(4),
        ROOT / "runs/engine-example" / kind,
    )
    rows.append(r)
(ROOT / "runs/engine-example/experiment.json").write_text(
    json.dumps(
        dict(
            status="ILLUSTRATIVE_LITERATURE_PLOT_DERIVED_NOT_VALIDATED_COMBUSTION",
            source_report="runs/reference-engine/report.json",
            limitations=report["metadata"]["limitations"],
            results=rows,
        ),
        indent=2,
    )
)
