"""Render Phase 4 figures from actual CAD, Gmsh and CalculiX outputs."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from conrod.fea import von_mises
from conrod.fields import integration_coordinates

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
FIG = ROOT / "docs/phase4/final/figures"
EVIDENCE = json.loads((ROOT / "data/phase4/phase4-evidence.json").read_text())


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _stress_plot(case, out):
    fields_path = RUNS / f"phase4-refined/P4-0065/local-0.5mm/{case}/fields.json"
    fields = load_json(fields_path)
    stress = np.asarray(fields["integration_point_stress"], dtype=float)
    coords = integration_coordinates(fields["nodes"], fields["elements"], stress)
    vm = von_mises(stress[:, 2:])
    rng = np.random.default_rng(24680)
    sample = rng.choice(len(vm), min(25000, len(vm)), replace=False)
    top = np.argpartition(vm, -min(2500, len(vm)))[-min(2500, len(vm)) :]
    ids = np.unique(np.concatenate([sample, top]))
    fig = plt.figure(figsize=(8.5, 5.8))
    ax = fig.add_subplot(111, projection="3d")
    points = ax.scatter(
        coords[ids, 0],
        coords[ids, 1],
        coords[ids, 2],
        c=vm[ids],
        cmap="inferno",
        s=1.0,
        alpha=0.75,
        vmin=0,
        vmax=394.444444444,
    )
    ax.set_title(f"P4-0065 {case}: raw CalculiX integration-point von Mises stress")
    ax.set_xlabel("Rod axis x (mm)")
    ax.set_ylabel("Width y (mm)")
    ax.set_zlabel("Depth z (mm)")
    ax.set_box_aspect((145, 45, 35))
    ax.view_init(elev=24, azim=-115)
    bar = fig.colorbar(points, ax=ax, pad=0.08, shrink=0.75)
    bar.set_label("Unaveraged IP von Mises (MPa); color capped at allowable")
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return float(vm.max()), len(vm)


def _displacement_plot(out):
    fields = load_json(RUNS / "phase4-refined/P4-0065/local-0.5mm/tension/fields.json")
    ids = np.array([int(k) for k in fields["nodes"]])
    xyz = np.array([fields["nodes"][str(i)] for i in ids])
    u = np.array([fields["displacement"][str(i)] for i in ids])
    mag = np.linalg.norm(u, axis=1)
    rng = np.random.default_rng(13579)
    sample = rng.choice(len(ids), min(28000, len(ids)), replace=False)
    top = np.argpartition(mag, -min(1800, len(mag)))[-min(1800, len(mag)) :]
    pick = np.unique(np.concatenate([sample, top]))
    fig = plt.figure(figsize=(8.5, 5.8))
    ax = fig.add_subplot(111, projection="3d")
    points = ax.scatter(
        xyz[pick, 0],
        xyz[pick, 1],
        xyz[pick, 2],
        c=mag[pick],
        cmap="viridis",
        s=1.1,
        alpha=0.8,
    )
    ax.set_title("P4-0065 tension: CalculiX nodal displacement magnitude")
    ax.set_xlabel("Rod axis x (mm)")
    ax.set_ylabel("Width y (mm)")
    ax.set_zlabel("Depth z (mm)")
    ax.set_box_aspect((145, 45, 35))
    ax.view_init(elev=24, azim=-115)
    fig.colorbar(points, ax=ax, pad=0.08, shrink=0.75, label="|U| (mm)")
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return float(mag.max())


def _cad_comparison(out):
    paths = [
        ROOT.parent / "phase3-rod/runs/phase3-refinement/0.35-tension/geometry.stl",
        RUNS / "phase4-refined/P4-0065/local-0.5mm/compression/geometry.stl",
    ]
    labels = [
        "Phase 3 baseline · 735.3 g · fails stress",
        "Phase 4 P4-0065 · 866.9 g · feasible under stated checks",
    ]
    fig = plt.figure(figsize=(12, 5.4))
    for i, (path, label) in enumerate(zip(paths, labels), start=1):
        mesh = trimesh.load(path, force="mesh")
        ax = fig.add_subplot(1, 2, i, projection="3d")
        faces = mesh.faces
        stride = max(1, len(faces) // 6500)
        triangles = mesh.vertices[faces[::stride]]
        collection = Poly3DCollection(
            triangles, facecolor="#8ca6bf", edgecolor="none", alpha=0.98
        )
        ax.add_collection3d(collection)
        bounds = mesh.bounds
        ax.set_xlim(bounds[0][0], bounds[1][0])
        ax.set_ylim(bounds[0][1], bounds[1][1])
        ax.set_zlim(bounds[0][2], bounds[1][2])
        ax.set_box_aspect(np.maximum(bounds[1] - bounds[0], 1))
        ax.view_init(elev=25, azim=-115)
        ax.set_title(label, fontsize=9)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        ax.set_zlabel("z (mm)")
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _mesh_plot(out):
    fields = load_json(
        RUNS / "phase4-refined/P4-0065/local-0.5mm/compression/fields.json"
    )
    xyz = np.array(list(fields["nodes"].values()), dtype=float)
    zmid = 26.970405517717 / 2
    slab = xyz[np.abs(xyz[:, 2] - zmid) <= 0.6]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.scatter(slab[:, 0], slab[:, 1], s=1, c="#315d86", alpha=0.55)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Rod axis x (mm)")
    ax.set_ylabel("Width y (mm)")
    ax.set_title(
        f"P4-0065 Gmsh 4.15.2 section mesh · 0.5 mm local target · {len(xyz):,} nodes"
    )
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _feasibility_plot(out):
    rows = load_json(ROOT / "data/phase4/family-screen.json")
    fine = EVIDENCE["refined_candidates"]
    palette = {
        "i_section": "#457b9d",
        "h_section": "#e76f51",
        "tapered": "#8d5fd3",
        "ribbed": "#2a9d8f",
        "pocket_variant": "#e9a23b",
    }
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    for kind, ax in zip(("compression", "tension"), axes):
        for family, color in palette.items():
            subset = [
                r
                for r in rows
                if r["family"] == family
                and r["load"] == kind
                and r["status"] == "FEA_SUCCESS"
            ]
            ax.scatter(
                [r["mass_g"] for r in subset],
                [r["max_stress_mpa"] for r in subset],
                s=30,
                alpha=0.7,
                color=color,
                label=family.replace("_", " "),
            )
        ax.axhline(
            394.444444,
            color="#b42318",
            linestyle="--",
            linewidth=1.5,
            label="Allowable 394.44 MPa",
        )
        for row in fine:
            level = "0.5" if row["candidate_id"] == "P4-0065" else "0.75"
            stress = row["mesh_levels"][level][kind]["peak_unaveraged_ip_von_mises_mpa"]
            marker = (
                "D" if row["assessment"]["recorded_screen_status"] == "PASS" else "X"
            )
            ax.scatter(
                row["actual_cad_mass_g"],
                stress,
                marker=marker,
                s=70,
                edgecolor="black",
                linewidth=0.5,
                color="#111827",
                zorder=5,
            )
            if row["candidate_id"] in ("P4-0065", "P4-0055", "P4-0059"):
                ax.annotate(
                    row["candidate_id"],
                    (row["actual_cad_mass_g"], stress),
                    xytext=(4, 5),
                    textcoords="offset points",
                    fontsize=8,
                )
        ax.set_title(kind.capitalize())
        ax.set_xlabel("Actual CAD mass (g)")
        ax.set_ylabel("Peak unaveraged integration-point stress (MPa)")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=7, loc="upper right")
    fig.suptitle("Phase 4 recorded numerical screens · not mechanical qualification")
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _mesh_trend_plot(out):
    candidates = {r["candidate_id"]: r for r in EVIDENCE["refined_candidates"]}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for candidate_id, color in (("P4-0055", "#457b9d"), ("P4-0065", "#e76f51")):
        row = candidates[candidate_id]
        levels = sorted((float(x) for x in row["mesh_levels"]), reverse=True)
        for ax, kind, field, label in (
            (
                axes[0],
                "compression",
                "peak_unaveraged_ip_von_mises_mpa",
                "Stress (MPa)",
            ),
            (axes[1], "tension", "peak_unaveraged_ip_von_mises_mpa", "Stress (MPa)"),
        ):
            xs = [x for x in levels]
            ys = [row["mesh_levels"][str(x)][kind][field] for x in levels]
            ax.plot(xs, ys, marker="o", linewidth=2, color=color, label=candidate_id)
            ax.set_xlabel("Local mesh target (mm); finer ←")
            ax.set_ylabel(label)
            ax.grid(alpha=0.2)
    axes[0].set_title("Compression refinement")
    axes[1].set_title("Tension refinement")
    axes[1].axhline(
        394.444444, color="#b42318", linestyle="--", linewidth=1.2, label="Allowable"
    )
    axes[0].legend()
    axes[1].legend()
    fig.suptitle("Non-nested local mesh response; no GCI claimed")
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    _cad_comparison(FIG / "phase4-cad-comparison.png")
    _mesh_plot(FIG / "phase4-final-mesh.png")
    _feasibility_plot(FIG / "phase4-feasibility-map.png")
    _mesh_trend_plot(FIG / "phase4-mesh-trend.png")
    stress_max, ip_count = _stress_plot(
        "compression", FIG / "phase4-compression-ip-stress.png"
    )
    tension_max, _ = _stress_plot("tension", FIG / "phase4-tension-ip-stress.png")
    displacement_max = _displacement_plot(FIG / "phase4-tension-displacement.png")
    print(
        json.dumps(
            {
                "figures": sorted(x.name for x in FIG.glob("*.png")),
                "raw_ip_peak_compression_mpa": stress_max,
                "raw_ip_peak_tension_mpa": tension_max,
                "integration_points": ip_count,
                "max_nodal_displacement_mm": displacement_max,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
