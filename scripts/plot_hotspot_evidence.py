"""Scientific plots from actual fields, not screenshots or synthetic contours."""

import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from conrod.fea import ROOT, von_mises
from conrod.fields import integration_coordinates

out = ROOT / "evidence/phase2"
out.mkdir(parents=True, exist_ok=True)
fig = plt.figure(figsize=(14, 7))
for index, kind in enumerate(["compression", "tension"], 1):
    directory = ROOT / "runs/focused-refinement" / ("0.75-" + kind)
    d = json.loads((directory / "fields.json").read_text())
    r = json.loads((directory / "result.json").read_text())
    xyz = integration_coordinates(
        d["nodes"], d["elements"], d["integration_point_stress"]
    )
    vm = von_mises(np.asarray(d["integration_point_stress"])[:, 2:])
    peak = int(np.argmax(vm))
    ids = np.unique(np.r_[np.arange(0, len(vm), max(1, len(vm) // 12000)), peak])
    ax = fig.add_subplot(1, 2, index, projection="3d")
    sc = ax.scatter(
        xyz[ids, 0],
        xyz[ids, 1],
        xyz[ids, 2],
        c=vm[ids],
        s=1,
        cmap="turbo",
        vmin=0,
        vmax=vm.max(),
    )
    ax.scatter(*xyz[peak], c="red", marker="x", s=70)
    ax.set(
        xlabel="Rod axis x (mm)",
        ylabel="y (mm)",
        zlabel="z (mm)",
        title=f"{kind.title()}: peak {vm[peak]:.1f} MPa\nActual unaveraged Gauss-point field; NOT CONVERGED",
    )
    ax.set_box_aspect((3, 1, 0.7))
    ax.view_init(25, -65)
    ax.set_xticks([0, 50, 100, 150])
    ax.set_yticks([-25, 0, 25])
    ax.set_zticks([0, 10, 20])
    ax.text2D(
        0.02,
        0.92,
        "Peak xyz (mm): " + ", ".join(f"{v:.2f}" for v in xyz[peak]),
        transform=ax.transAxes,
        fontsize=9,
    )
    fig.colorbar(
        sc,
        ax=ax,
        shrink=0.7,
        pad=0.08,
        orientation="horizontal",
        label="von Mises (MPa)",
    )
fig.tight_layout()
fig.savefig(out / "actual-hotspots.png", dpi=180)
print("Saved actual field figure")
