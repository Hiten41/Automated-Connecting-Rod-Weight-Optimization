"""Sequential, checkpointed refinement of the observed critical transition."""

import json
from conrod.fea import ROOT, solve
from conrod.schemas import Geometry, LoadCase, MeshSettings
from conrod.materials import MATERIALS


def run():
    root = ROOT / "runs/phase3-refinement"
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    # Pilot estimates: historical .5 all-feature mesh 113546 nodes; hard
    # 250000-node pre-solve cap and 600-second solver cap remain enforced.
    for h in [0.75, 0.5, 0.35, 0.25]:
        for kind, force in [("compression", 28000), ("tension", 18000)]:
            out = root / f"{h}-{kind}"
            path = out / "result.json"
            if path.exists():
                r = json.loads(path.read_text(encoding="utf-8"))
            else:
                r = solve(
                    Geometry(),
                    MATERIALS["Forged Steel (AISI 4340)"],
                    LoadCase(kind, force),
                    MeshSettings(
                        4, hotspot_size_mm=h, refinement_region="big_end_transition"
                    ),
                    out,
                )
            rows.append(r)
            (root / "results.json").write_text(
                json.dumps(rows, indent=2), encoding="utf-8"
            )
            print(
                h,
                kind,
                r["status"],
                r.get("node_count"),
                r.get("max_von_mises_mpa"),
                r.get("error"),
                flush=True,
            )
            if r["status"] != "FEA_SUCCESS":
                # Stop to inspect the failure before more expensive levels.
                return


if __name__ == "__main__":
    run()
