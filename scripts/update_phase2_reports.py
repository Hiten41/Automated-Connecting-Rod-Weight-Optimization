"""Generate reports only from existing executed records; safe to rerun."""

import json
import pandas as pd
from conrod.fea import ROOT
from package_evidence import portable


def load(relative, default=None):
    p = ROOT / relative
    return json.loads(p.read_text()) if p.exists() else default


def write(name, text):
    for old, new in [
        ("Phase1", "Phase 1"),
        ("Phase2", "Phase 2"),
        ("fixed1 mm", "fixed 1 mm"),
        ("Historical120", "Historical 120"),
        ("global4 mm", "global 4 mm"),
        ("is143.5", "is 143.5"),
        ("baseline735", "baseline 735"),
        ("mass735", "mass 735"),
        ("FoS1.8", "FoS 1.8"),
        ("above5%", "above 5%"),
        ("nominal4 mm", "nominal 4 mm"),
        ("gave477", "gave 477"),
        ("versus462", "versus 462"),
    ]:
        text = text.replace(old, new)
    (ROOT / "docs" / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def run():
    e = ROOT / "evidence/phase2"
    e.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for directory in [
        "phase2-experiments",
        "focused-refinement",
        "fillet-feasibility",
        "reference-engine",
        "historical-hotspots",
        "phase2-optimization",
        "engine-example",
        "phase2-diagnostic-verification",
    ]:
        for name in [
            "results.json",
            "convergence.json",
            "report.json",
            "optimization.json",
            "experiment.json",
            "verification.json",
        ]:
            p = ROOT / "runs" / directory / name
            if p.exists():
                (e / (directory + "-" + name)).write_text(
                    json.dumps(portable(json.loads(p.read_text())), indent=2),
                    encoding="utf-8",
                )
    global_rows = load("runs/phase2-experiments/results.json", [])
    budgets = {b["case"]: b for b in load("evidence/phase2/mesh-budget-audit.json", [])}
    for record in global_rows:
        key = record["output_dir"].replace("\\", "/").split("/")[-1]
        if key in budgets:
            record["node_count"] = budgets[key]["node_count"]
            record["element_count"] = budgets[key]["element_count"]
    focused = load("runs/focused-refinement/results.json", [])
    convergence = load("runs/focused-refinement/convergence.json", {})
    for family, rows in [("global", global_rows), ("focused", focused)]:
        for r in rows:
            all_rows.append(
                dict(
                    family=family,
                    status=r["status"],
                    load=r["load"]["kind"],
                    boundary=r["mesh"]["boundary_mode"],
                    global_mm=r["mesh"]["size_mm"],
                    local_mm=r["mesh"].get("hotspot_size_mm"),
                    mass_g=r.get("mass_kg", 0) * 1000,
                    stress_mpa=r.get("max_von_mises_mpa"),
                    displacement_mm=r.get("max_displacement_mm"),
                    fos=r.get("factor_of_safety"),
                    nodes=r.get("node_count"),
                    elements=r.get("element_count"),
                    runtime_s=r.get("runtime_s"),
                    hotspot=r.get("hotspot"),
                    error=r.get("error"),
                )
            )
    pd.DataFrame(all_rows).to_csv(e / "experiments.csv", index=False)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for kind in ["compression", "tension"]:
        rows = [
            r
            for r in focused
            if r["load"]["kind"] == kind and r["status"] == "FEA_SUCCESS"
        ]
        x = [r["mesh"]["hotspot_size_mm"] for r in rows]
        for ax, key, label in zip(
            axes,
            ["max_von_mises_mpa", "max_displacement_mm"],
            ["Peak unaveraged VM (MPa)", "Maximum displacement (mm)"],
        ):
            ax.plot(x, [r[key] for r in rows], "o-", label=kind)
            ax.set(xlabel="Local target size (mm); bulk 4 mm", ylabel=label)
            ax.grid(alpha=0.2)
    for ax in axes:
        ax.invert_xaxis()
        ax.legend()
    fig.tight_layout()
    fig.savefig(e / "convergence.png", dpi=180)
    plt.close(fig)
    mesh = (
        "# Mesh convergence — Phase 2\n\nStatus from executed focused studies: "
        + json.dumps({k: v["status"] for k, v in convergence.items()})
        + ".\n\n"
    )
    mesh += "Global4,2.5,1.75,1.25 mm meshes were generated. Finer global cases exceeded the250000-node solve budget; their failed records and meshes are retained. Global1 mm was not attempted after that resource limit. A separate focused series uses4 mm bulk and local1.75,1.25,1.0,0.75 mm targets around junction/pocket-corner neighborhoods. These are distinct refinement families, not equivalent global mesh sizes.\n\n"
    for kind in ["compression", "tension"]:
        mesh += "## " + kind.title() + "\n\n"
        for r in focused:
            if r["load"]["kind"] != kind:
                continue
            if r["status"] != "FEA_SUCCESS":
                mesh += "- Failed: " + r.get("error", "unknown") + "\n"
                continue
            mesh += f"- Local {r['mesh']['hotspot_size_mm']} mm: {r['node_count']} nodes / {r['element_count']} elements; peak {r['max_von_mises_mpa']:.3f} MPa; U {r['max_displacement_mm']:.6f} mm; FoS {r['factor_of_safety']:.4f}; {r['runtime_s']:.1f} s; hotspot {r['hotspot']['coordinates_mm']} mm, element {r['hotspot']['element_id']}, IP {r['hotspot']['integration_point']}.\n"
        mesh += "\n"
    mesh += "A repeated nominal4 mm bearing compression mesh gave477.73 MPa in the pilot versus462.27 MPa in the comparison. Gmsh multithreaded mesh variability and stress sampling therefore matter; preserved decks are the reproducibility reference, not a bitwise-regeneration promise. Displacement stabilizes, but peak stress varies above5% in successive refinements. Hotspots remain at the big-end/shank transition, not the gauge nodes. This is not enough to declare a mathematical singularity: finite-radius concentrations, geometric resolution and discrete bearing-load quadrature remain competing explanations. Local2 mm IP means are descriptive, unweighted and centered on the moving peak; they are not substituted for the maximum to make a design pass. No mechanically qualified design is claimed. Further investigation needs controlled surface quadrature, a deterministic mesh study and additional resolution through the fillets.\n\n![Actual refinement plots](../evidence/phase2/convergence.png)\n\nFull coordinates, quality and runtimes: `evidence/phase2/experiments.csv` and compact result JSON. Gauss coordinates use quadratic C3D10 shape functions with CalculiX gauss3d5 ordering, verified on an affine tetrahedron. Historical Phase1 hotspots are independently reconstructed in `historical-hotspots-report.json`; original raw records remain unchanged.\n"
    write("MESH_CONVERGENCE.md", mesh)
    reference = load("runs/reference-engine/report.json", {})
    summary = "# Phase 2 validation report\n\nResearch prototype; no mechanically qualified design.\n\n## Engine reference\n\n"
    if reference:
        p = reference["peaks"]
        summary += f"Approximate published-plot-derived peak compression {p['compression_n']:.2f} N at {p['compression_angle_deg']:.2f} degrees; tension {p['tension_n']:.2f} N at {p['tension_angle_deg']:.2f} degrees. Independently plotted rod-force peak approximately {reference['observed_rod_peak_n']:.0f} N; sparse-point comparison MAE {reference['rod_comparison_mae_n']:.2f} N. This mismatch is not concealed or fitted away. Exact derivative versus finite-difference maximum error {reference['kinematics']['max_finite_difference_error_m_s2']:.6g} m/s². TDC/BDC positions reproduce0/86 mm. See ENGINE_LOAD_MODEL.md for sources, mass definition and missing raw pressure data. Combustion loading is NOT experimentally validated.\n\n"
    summary += "## Actual FEA\n\n"
    summary += f"{sum(r['status'] == 'FEA_SUCCESS' for r in global_rows + focused)} successful baseline comparison/refinement solves; {sum(r['status'] != 'FEA_SUCCESS' for r in global_rows + focused)} explicitly failed/over-budget attempts. These counts exclude the pilot, datasets, optimization and engine example. Filleted baseline CAD mass735.327 g. Both bearing load directions fail the requested baseline FoS1.8. See MESH_CONVERGENCE.md and BOUNDARY_CONDITION_COMPARISON.md.\n\n"
    engine_case = load("runs/engine-example/experiment.json", {})
    if engine_case:
        summary += "## Experiment D — illustrative reference loads\n\nCAD center distance is143.5 mm to match the reference kinematics; other rod dimensions are the research design, not measured production-rod dimensions. COSINE_BEARING, global4 mm with curve refinement. Not experimentally validated combustion.\n\n"
        for r in engine_case.get("results", []):
            if r.get("status") == "FEA_SUCCESS":
                summary += f"- {r['load']['kind']}: {r['load']['force_n']:.2f} N; mass {r['mass_kg'] * 1000:.3f} g; stress {r['max_von_mises_mpa']:.3f} MPa; U {r['max_displacement_mm']:.6f} mm; FoS {r['factor_of_safety']:.3f}; runtime {r['runtime_s']:.1f} s. No geometry-specific convergence established.\n"
        summary += "\n"
    model = load("models/phase2_surrogate.json")
    ml = "# Phase 2 ML evaluation\n\nHistorical120 Phase1 analyses are excluded from Phase2 training. Geometry/BC/fidelity/version mismatch raises an error. Radius is fixed1 mm; five other section dimensions vary. Learned targets use exact linear-static stress/F and displacement*E/F scaling to remove known load/modulus dependence. Geometry groups prevent related compression/tension cases leaking across splits.\n\n"
    if model:
        ml += f"Dataset: {model['sample_count']} actual solver analyses. Split {model['split_counts']}; selected {model['selected_model']}. Group separation: {model['groups_disjoint']}.\n\n"
        for name, score in model["comparisons"].items():
            ml += "## " + name + "\n\n"
            for target, value in score["test"].items():
                ml += f"- {target}: MAE {value['MAE']:.6g}, RMSE {value['RMSE']:.6g}, R² {value['R2']:.6g}.\n"
            ml += "\n"
        ml += f"Near-constraint test count: {model['near_constraint_test_count']}; metrics: {model['near_constraint_metrics']}. Sparse coverage is not proof of accurate feasibility-boundary prediction. Observed residual allowance {model['residual_margin']} is not calibrated confidence. The1.2 multiplier remains a labelled heuristic. Coarse8 mm training is not converged truth.\n\n"
        summary += f"## ML\n\n{model['sample_count']} compatible records; selected {model['selected_model']}; held-out metrics and limitations in ML_EVALUATION.md.\n\n"
    else:
        ml += "No completed Phase2 model evaluation exists yet.\n\n"
    multi = load("data/phase2/multifidelity.json")
    if multi:
        ml += (
            "## Paired-fidelity investigation\n\n```json\n"
            + json.dumps(multi, indent=2)
            + "\n```\n\nThe correction is not promoted to optimization based on this small test.\n"
        )
    write("ML_EVALUATION.md", ml)
    opt = load("runs/phase2-optimization/optimization.json")
    summary += "## Optimization\n\n"
    if opt:
        summary += f"Status: **{opt['status']}**. New multistart optimization used Phase2 geometry/BC/labels. Baseline mass: {opt.get('baseline_mass_kg')}; optimized mass: {opt.get('optimized_mass_kg')}; reduction: {opt.get('mass_reduction_pct')}. Missing values mean no accepted new design, not zero mass or zero error.\n\n"
        if opt.get("error"):
            summary += "Error: " + opt["error"] + "\n\n"
        summary += f"Recorded starts: {len(opt.get('diagnostics', []))}; optimizer-admitted FEA verification attempts: {len(opt.get('verification_attempts', []))}. All candidate reasons and margins are retained in evidence/phase2/phase2-optimization-optimization.json. Mesh-dependent passes are provisional, never hardware qualification.\n\n"
    else:
        summary += "Not completed yet; no new optimum is claimed.\n\n"
    diagnostic = load("runs/phase2-diagnostic-verification/verification.json", {})
    if diagnostic:
        summary += "### Independent checks of rejected optimizer points\n\nThese are diagnostic designs, not accepted optima or qualified hardware. No mass-reduction claim follows from an optimizer failure.\n\n"
        for i, candidate in enumerate(diagnostic.get("candidates", []), 1):
            summary += f"Candidate {i}: single-mesh constraint pass={candidate['constraint_pass_at_one_mesh']}; rejection reasons={candidate['reasons']}.\n\n"
            for r in candidate["fea"]:
                if r.get("status") == "FEA_SUCCESS":
                    summary += f"- {r['load']['kind']}: mass {r['mass_kg'] * 1000:.3f} g; stress {r['max_von_mises_mpa']:.3f} MPa; U {r['max_displacement_mm']:.6f} mm; FoS {r['factor_of_safety']:.3f}.\n"
            summary += "\n"
    summary += "## Quality and limitations\n\nActual FreeCAD FEM imports pass preflight. Python tests and external integration evidence are recorded separately. Browser inspection is blocked by `Local browser use is disabled in Work settings`; functional AppTest/HTTP checks do not replace visual QA. No screenshots fabricated. Raw input decks/logs/fields remain locally reproducible; portable compact evidence includes source hashes when packaged. Phase1 and upstream histories are preserved. Remaining issues: unconverged peaks, approximate pressure reference, small coarse-data ML domain, no fatigue/contact/thermal/plastic/nonlinear stability certification.\n"
    write("VALIDATION_REPORT.md", summary)
    write(
        "FEA_VALIDATION.md",
        "# FEA validation\n\n"
        + summary.split("## Actual FEA")[1].split("## ML")[0]
        + "\nSee MESH_CONVERGENCE.md for exact refinement evidence. Unit tests cover force signs, resultant/moment balance, positive bearing weights, Gauss mapping, explicit failure and convergence rejection. External tests execute CAD exports and a same-mesh linear load-scaling solve. Hosted CI covers Python only.\n",
    )
    comparison = "# Phase 1 versus Phase 2\n\nPhase1 historical: sharp pockets, full big-bore clamp, uniform global traction over small bore, manual28/18 kN. Baseline734.577 g; provisional optimized384.418 g; reduction47.668%. Final1.75 mm compression352.931 MPa and U0.117279 mm; tension226.974 MPa. Peak-stress convergence was not established. Preserved branch commit1f5b5c44.\n\nPhase2 baseline:1 mm transition/pocket fillets, mass735.327 g. Experiment B isolates fillets under legacy BC; C changes to compressive cosine bearing loads. D is explicitly approximate published-plot-derived illustration, not validated combustion. E is a new optimization with new labels. No47.668% result is carried forward.\n\n"
    comparison += "Original Phase 1 baseline at4 mm: compression225.597 MPa /0.060653 mm, tension145.031 MPa /0.038988 mm. Its geometry/material/loads match the initial Phase 2 baseline except fillets. Phase 2 also adds local refinement, so this is not an isolated, converged estimate of fillet benefit. Fillets did not lower the recorded peaks or establish convergence; no stress-reduction claim is made. The source records and hashes are preserved in evidence/phase2/phase1-baseline-comparison.json.\n\n"
    for r in global_rows:
        if r["status"] == "FEA_SUCCESS":
            comparison += f"- {r['mesh']['boundary_mode']} / {r['load']['kind']} at4 mm: {r['max_von_mises_mpa']:.3f} MPa, {r['max_displacement_mm']:.6f} mm, FoS {r['factor_of_safety']:.4f}; hotspot {r['hotspot']['region']}.\n"
    comparison += "\nThe BC comparison changes ring deformation and loading direction; stresses are not interchangeable. Both Phase2 bearing baseline cases fail FoS1.8 and the focused refinement study does not establish converged peaks. Any new optimum is governed by the Phase2 report, not the historical claim.\n"
    write("PHASE1_VS_PHASE2.md", comparison)
    print("Reports regenerated from recorded evidence")


if __name__ == "__main__":
    run()
