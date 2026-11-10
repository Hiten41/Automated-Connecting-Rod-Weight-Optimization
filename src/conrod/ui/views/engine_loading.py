"""Engine kinematics and load-provenance page."""

import io

import numpy as np
import pandas as pd
import streamlit as st

from conrod.design_families import FamilyDesign
from conrod.engine import Engine, calculate, plots, pressure_csv
from conrod.schemas import Geometry, LoadCase


def render_engine_loading(root, read, advanced_diagnostics):
    st.subheader("Loads with explicit provenance")
    mode = st.radio("Loading mode", ["Manual forces", "Engine-derived loading"])
    if mode == "Manual forces":
        with st.form("manual"):
            c = st.number_input("Peak compression (N)", min_value=1.0, value=28000.0)
            t = st.number_input("Peak tension (N)", min_value=1.0, value=18000.0)
            if st.form_submit_button("Use manual loads"):
                st.session_state.loads = [
                    LoadCase("compression", c).to_dict(),
                    LoadCase("tension", t).to_dict(),
                ]
                st.session_state.load_provenance = "MANUAL_USER_FORCES"
                st.success("Manual analysis configuration saved.")
    else:
        source = st.selectbox(
            "Pressure source",
            ["Upload pressure CSV", "Published Hydra plot comparison (approximate)"],
        )
        metadata = read(root / "data/reference_engine/metadata.json")
        if source.startswith("Published"):
            st.warning(
                "Approximate readings from published gas-force plot, not raw cylinder-pressure data. Cross-publication dimensions and neglected dynamics prevent an experimental combustion validation claim."
            )
            st.markdown(
                "[Mufti thesis, Fig 7.2 / 7.4](https://etheses.whiterose.ac.uk/id/eprint/5354/1/414535.pdf) · [Mufti & Priest, Table 1](https://doi.org/10.1115/1.3176988)"
            )
            with st.expander("Source definitions and limitations"):
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Reference parameter": key.replace("_", " ").title(),
                                "Value": value,
                            }
                            for key, value in metadata.get("engine", {}).items()
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Published gas-force readings are approximate plot extractions, not raw cylinder-pressure data."
                )
                advanced_diagnostics(metadata)
        with st.form("engine"):
            a, b, c = st.columns(3)
            bore = a.number_input("Cylinder bore (mm)", min_value=0.1, value=85.99)
            stroke = b.number_input("Stroke (mm)", min_value=0.1, value=86.0)
            rod = c.number_input("Rod center distance (mm)", min_value=0.1, value=143.5)
            rpm = a.number_input("RPM", min_value=0.0, value=1500.0)
            mass = b.number_input(
                "Effective reciprocating mass (kg)",
                min_value=0.0,
                value=0.5778,
                format="%.4f",
            )
            cycle = c.selectbox("Cycle (degrees)", [720, 360])
            rod_mass = a.number_input(
                "Additional rod mass (kg)", min_value=0.0, value=0.0
            )
            rod_cg = b.number_input(
                "Rod CG fraction from crank pin",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
            )
            st.caption(
                "Optional two-end mass approximation: leave additional rod mass zero if effective reciprocating mass already includes its share. Reference rod mass/CG are not measured inputs here."
            )
            unit = st.selectbox("CSV pressure unit", ["bar", "MPa", "Pa"])
            upload = st.file_uploader(
                "CSV: angle_deg, pressure, optional reference_pressure", type="csv"
            )
            st.caption(
                "0 = firing TDC. Include 0 and cycle endpoint with matching pressure differential. Missing reference_pressure means the supplied pressure is differential. No extrapolation. Effective mass must not include the whole rod by default."
            )
            run = st.form_submit_button("Calculate cycle")
        if run:
            try:
                e = Engine(bore, stroke, rod, rpm, mass, cycle, rod_mass, rod_cg)
                if source.startswith("Published"):
                    if e != Engine(**metadata["engine"]):
                        raise ValueError(
                            "Published comparison requires the exact sourced preset; use CSV mode for other parameters."
                        )
                    observed = pd.read_csv(
                        root / "data/reference_engine/mufti_fig7_2_readings.csv"
                    )
                    p = pd.DataFrame(
                        {
                            "angle_deg": observed.angle_deg,
                            "pressure_pa": observed.gas_force_n
                            / (np.pi * (bore / 1000) ** 2 / 4),
                            "reference_pa": 0.0,
                        }
                    )
                    provenance = (
                        "APPROXIMATE_PUBLISHED_PLOT_NOT_EXPERIMENTALLY_VALIDATED"
                    )
                else:
                    if upload is None:
                        raise ValueError("Upload a complete pressure CSV.")
                    p = pressure_csv(io.BytesIO(upload.getvalue()), unit, cycle)
                    provenance = "USER_SUPPLIED_PRESSURE_NOT_INDEPENDENTLY_VALIDATED"
                frame, peaks = calculate(e, p)
                st.session_state.engine_result = (frame, peaks, provenance)
            except (
                ValueError,
                TypeError,
                KeyError,
                ArithmeticError,
                OSError,
                RuntimeError,
            ) as exc:
                st.error(
                    "Could not calculate the engine cycle from the supplied inputs."
                )
                advanced_diagnostics({"exception": str(exc)})
        if "engine_result" in st.session_state:
            frame, peaks, provenance = st.session_state.engine_result
            a, b = st.columns(2)
            a.metric(
                "Compression",
                f"{peaks['compression_n']:.1f} N",
                f"at {peaks['compression_angle_deg']:.2f}°",
            )
            b.metric(
                "Tension",
                f"{peaks['tension_n']:.1f} N",
                f"at {peaks['tension_angle_deg']:.2f}°",
            )
            st.caption(provenance)
            if st.button("Use these peak loads in FEA"):
                if min(peaks["compression_n"], peaks["tension_n"]) <= 0:
                    st.error(
                        "This cycle does not have both signed peaks; select a single nonzero case manually."
                    )
                else:
                    rod_length = peaks["engine"]["rod_length_mm"]
                    try:
                        family_design = st.session_state.get("phase4_family_design")
                        if family_design:
                            updated_family = FamilyDesign(
                                **{**family_design, "length_cc": rod_length}
                            ).validate()
                            updated_geometry = {
                                **st.session_state.geometry,
                                "length_cc": rod_length,
                            }
                        else:
                            updated_family = None
                            updated_geometry = (
                                Geometry(
                                    **{
                                        **st.session_state.geometry,
                                        "length_cc": rod_length,
                                    }
                                )
                                .validate()
                                .to_dict()
                            )
                    except ValueError as exc:
                        st.error(
                            "Cycle calculated, but its rod length is outside the active geometry bounds; "
                            "adjust the geometry before applying loads."
                        )
                        advanced_diagnostics({"geometry_length_validation": str(exc)})
                    else:
                        st.session_state.loads = [
                            LoadCase("compression", peaks["compression_n"]).to_dict(),
                            LoadCase("tension", peaks["tension_n"]).to_dict(),
                        ]
                        st.session_state.load_provenance = provenance
                        st.session_state.geometry = updated_geometry
                        if updated_family:
                            st.session_state.phase4_family_design = (
                                updated_family.to_dict()
                            )
                        st.success(
                            "Peak loads saved with provenance; geometry center distance was synchronized to the engine rod length."
                        )
            st.plotly_chart(plots(frame), width="stretch")
            st.download_button(
                "Download cycle CSV",
                frame.to_csv(index=False),
                "engine_cycle.csv",
                "text/csv",
            )
