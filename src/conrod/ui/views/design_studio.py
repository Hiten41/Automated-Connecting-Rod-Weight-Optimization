"""Parametric geometry-family design and paired FEA studio."""

import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from conrod.design_families import FAMILIES, FamilyDesign
from conrod.fea import cad, solve
from conrod.materials import MATERIALS
from conrod.phase4 import Phase4Constraints, assess_candidate
from conrod.schemas import LoadCase, MeshSettings, Mode
from conrod.visualization import cad_figure, solver_field_figure


def render_design_studio(root, advanced_diagnostics):
    st.subheader("Parametric geometry families")
    st.caption(
        "Bore diameters and 145 mm center distance match the historical reference. "
        "Mass is calculated from the generated FreeCAD solid and the historical steel density."
    )
    family_names = {
        "i_section": "I section",
        "h_section": "H section",
        "tapered": "Tapered I section",
        "ribbed": "Locally ribbed I section",
        "pocket_variant": "Rounded pocket H section",
    }
    family = st.selectbox(
        "Geometry family",
        FAMILIES,
        format_func=lambda value: family_names[value],
        key="phase4_family_select",
    )
    prior = st.session_state.get("phase4_family_design")
    if not prior or prior.get("family") != family:
        prior = FamilyDesign(family=family).to_dict()
    with st.form("phase4_geometry_form"):
        values = dict(prior)
        a, b, c = st.columns(3)
        values["ring_thickness"] = a.number_input(
            "Eye wall (mm)", 6.0, 12.0, float(prior["ring_thickness"]), 0.2
        )
        values["shank_width"] = b.number_input(
            "Shank width (mm)", 20.0, 44.0, float(prior["shank_width"]), 0.5
        )
        values["beam_thickness"] = c.number_input(
            "Section depth (mm)", 20.0, 36.0, float(prior["beam_thickness"]), 0.5
        )
        a, b, c = st.columns(3)
        values["flange_thickness_mm"] = a.number_input(
            "Flange / rail thickness (mm)",
            3.0,
            10.0,
            float(prior["flange_thickness_mm"]),
            0.25,
        )
        values["web_thickness_mm"] = b.number_input(
            "Web thickness (mm)", 3.0, 10.0, float(prior["web_thickness_mm"]), 0.25
        )
        values["transition_radius_mm"] = c.number_input(
            "Eye transition radius (mm)",
            0.5,
            4.0,
            float(prior["transition_radius_mm"]),
            0.1,
        )
        if family == "tapered":
            a, b, c = st.columns(3)
            for col, name, label in zip(
                (a, b, c),
                ("taper_big_width_mm", "taper_mid_width_mm", "taper_small_width_mm"),
                (
                    "Big end section width (mm)",
                    "Mid shank width (mm)",
                    "Small end section width (mm)",
                ),
            ):
                values[name] = col.number_input(
                    label, 20.0, 44.0, float(prior[name]), 0.5
                )
        if family == "ribbed":
            a, b = st.columns(2)
            values["rib_height_mm"] = a.number_input(
                "Rib height (mm)", 0.0, 6.0, float(prior["rib_height_mm"]), 0.25
            )
            values["rib_length_mm"] = b.number_input(
                "Rib run (mm)", 8.0, 35.0, float(prior["rib_length_mm"]), 1.0
            )
        if family == "pocket_variant":
            a, b = st.columns(2)
            values["pocket_length_mm"] = a.number_input(
                "Pocket length (mm)", 10.0, 48.0, float(prior["pocket_length_mm"]), 1.0
            )
            values["pocket_width_mm"] = b.number_input(
                "Pocket width (mm)", 6.0, 20.0, float(prior["pocket_width_mm"]), 0.5
            )
        a, b, c = st.columns(3)
        a.metric("Bore center distance", "145 mm")
        b.metric("Big / small bore", "50 / 24 mm")
        c.metric("Historical allowable", "394.44 MPa")
        create_cad = st.form_submit_button("Generate FreeCAD model")
        run_screen = st.form_submit_button("Run paired compression and tension FEA")
    resolution = st.selectbox(
        "Mesh level for paired FEA",
        [
            "Coarse screen · 6 mm",
            "Transition refinement · 1.25 mm",
            "Transition refinement · 0.75 mm",
            "Fine transition check · 0.5 mm",
        ],
        help="Fine levels take longer. A single mesh, coarse pass or stress-only pass does not certify a design; displacement, buckling and mesh-trend checks also apply.",
    )
    if create_cad or run_screen:
        try:
            design = FamilyDesign(**values).validate()
            st.session_state.phase4_family_design = design.to_dict()
            st.session_state.phase4_cad_output = None
            for key in ("length_cc", "big_end_id", "small_end_id"):
                st.session_state.geometry[key] = getattr(design, key)
            out = root / "runs/ui-phase4" / uuid.uuid4().hex[:12]
            if create_cad:
                with st.spinner("Generating and checking the FreeCAD solid…"):
                    meta = cad(design, out / "cad")
                st.session_state.phase4_cad_output = str(out / "cad")
                mass_g = (
                    meta["volume_mm3"]
                    * MATERIALS["Forged Steel (AISI 4340)"].density_kg_per_mm3
                    * 1000
                )
                st.success(
                    f"Valid one-solid CAD · {mass_g:.1f} g at the historical steel density · "
                    f"{meta['transition_edges_filleted']} transition edges rounded."
                )
            if run_screen:
                if resolution.startswith("Coarse"):
                    size, hotspot, local = 6.0, None, False
                else:
                    size, hotspot, local = (
                        4.0,
                        float(resolution.split("·")[-1].replace("mm", "").strip()),
                        True,
                    )
                settings = MeshSettings(
                    size_mm=size,
                    hotspot_size_mm=hotspot,
                    local_refinement=local,
                    refinement_region="big_end_transition",
                )
                out.mkdir(parents=True, exist_ok=True)
                material = MATERIALS["Forged Steel (AISI 4340)"]
                results = {}
                with st.spinner("Running FreeCAD → Gmsh → CalculiX load cases…"):
                    cdir = out / "compression"
                    results["compression"] = solve(
                        design,
                        material,
                        LoadCase("compression", 28000),
                        settings,
                        cdir,
                        Mode.FEA,
                    )
                    tdir = out / "tension"
                    results["tension"] = solve(
                        design,
                        material,
                        LoadCase("tension", 18000),
                        settings,
                        tdir,
                        Mode.FEA,
                        mesh_source=cdir
                        if results["compression"].get("status") == "FEA_SUCCESS"
                        else None,
                    )
                st.session_state.phase4_last_results = results
                st.session_state.phase4_last_dir = str(out)
            st.rerun()
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            st.error(
                "Could not generate or analyze this design. Review developer diagnostics for details."
            )
            advanced_diagnostics({"exception": str(exc)})
    st.caption(
        "Elastic inputs remain E = 205 GPa, ν = 0.29, density = 7850 kg/m³, "
        "historical yield assumption = 710 MPa. This is not a material certificate."
    )
    cad_dir = st.session_state.get("phase4_cad_output")
    if cad_dir and (Path(cad_dir) / "geometry.stl").exists():
        st.plotly_chart(cad_figure(Path(cad_dir) / "geometry.stl"), width="stretch")
        st.download_button(
            "Download FreeCAD model and parameters",
            (Path(cad_dir) / "geometry.FCStd").read_bytes(),
            "phase4-connecting-rod.FCStd",
            "application/octet-stream",
        )
    results = st.session_state.get("phase4_last_results")
    if results:
        rows = []
        for kind in ("compression", "tension"):
            r = results[kind]
            rows.append(
                {
                    "Load": kind.title(),
                    "Status": r.get("status"),
                    "Peak unaveraged IP stress (MPa)": r.get("max_von_mises_mpa"),
                    "Maximum displacement (mm)": r.get("max_displacement_mm"),
                    "Yield FoS on 710 MPa assumption": r.get("factor_of_safety"),
                    "Nodes": r.get("node_count"),
                    "Elements": r.get("element_count"),
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        constraints = Phase4Constraints()
        checks = [
            results[k].get("status") == "FEA_SUCCESS"
            and results[k].get("max_von_mises_mpa", float("inf"))
            <= constraints.allowable_stress_mpa
            and results[k].get("max_displacement_mm", float("inf"))
            <= constraints.maximum_displacement_mm
            for k in ("compression", "tension")
        ]
        if all(checks):
            st.info(
                "Both stress/displacement screens are inside the historical limits. Buckling and independent refinement remain required; this is not a feasibility claim."
            )
        else:
            st.error(
                "At least one actual FEA stress/displacement screen fails. This workflow remains screening only; no optimization is enabled by this result."
            )
        assessment = assess_candidate(results)
        st.markdown(
            f"**Recorded numerical screen:** {assessment.get('recorded_screen_status', 'UNVERIFIED')}"
        )
        st.caption(
            "Independent solver verification: NOT_PERFORMED · mechanical qualification: NOT_QUALIFIED · "
            "optimization eligibility: NOT_QUALIFIED."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {"Constraint": key.replace("_", " ").title(), "Value": value}
                    for key, value in assessment.get("constraints", {}).items()
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        advanced_diagnostics(assessment)
        last_dir = st.session_state.get("phase4_last_dir")
        if last_dir:
            for kind in ("compression", "tension"):
                field = Path(last_dir) / kind / "fields.json"
                if field.exists():
                    with st.expander(f"Inspect {kind} solver field"):
                        st.plotly_chart(solver_field_figure(field), width="stretch")
