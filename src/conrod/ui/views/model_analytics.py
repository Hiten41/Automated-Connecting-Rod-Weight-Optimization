"""Model analytics views with Phase 4 and historical datasets separated."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_model_analytics(
    root,
    read,
    load_phase4_ml_evaluation,
    phase4_prediction_records,
    advanced_diagnostics,
):
    st.subheader("Phase 4 exploratory model evaluation")
    analytics_diagnostics = {}
    p4 = load_phase4_ml_evaluation(root)
    if p4 is not None:
        dataset = p4.get("dataset", {})
        summary = st.columns(4)
        summary[0].metric("Phase 4 load-case records", dataset.get("rows", "N/A"))
        summary[1].metric("Coarse rows", dataset.get("coarse_rows", "N/A"))
        summary[2].metric("Refined rows", dataset.get("refined_rows", "N/A"))
        summary[3].metric(
            "Independent geometry groups",
            dataset.get("coarse_geometry_groups", "N/A"),
        )
        st.caption(
            f"Grouping key: {dataset.get('grouping_key', 'Not recorded')} · "
            f"{dataset.get('coarse_fold_count', 'N/A')}-fold coarse cross-validation · "
            f"{dataset.get('fine_holdout_geometry_groups', 'N/A')} fine-holdout geometry groups. "
            "Geometry groups are disjoint across folds and across the fine holdout."
        )
        st.warning(
            "Phase 4 models are exploratory. The fine holdout has only six geometries, "
            "shows fidelity shift, and is not eligible for structural constraint enforcement. "
            "Its best recorded stress MAE (69.02 MPa) exceeds P4-0065's 28.44 MPa tension headroom."
        )
        metric_rows = []
        for split_name, split_title in (
            ("coarse_grouped_5fold_oof", "Coarse grouped 5-fold OOF"),
            ("coarse_trained_fine_geometry_holdout", "Fine geometry holdout"),
        ):
            for model, values in p4.get(split_name, {}).items():
                metric_rows.append(
                    {
                        "Evaluation": split_title,
                        "Model": model,
                        "Rows": values.get("n"),
                        "MAE (MPa)": values.get("mae_mpa"),
                        "RMSE (MPa)": values.get("rmse_mpa"),
                        "R²": values.get("r2"),
                    }
                )
        if metric_rows:
            st.dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")
        predictions = pd.DataFrame(phase4_prediction_records(p4))
        if not predictions.empty:
            eval_label = st.selectbox(
                "Prediction records",
                [
                    "coarse_grouped_5fold_oof",
                    "coarse_trained_fine_geometry_holdout",
                ],
                format_func=lambda value: (
                    "Coarse grouped out-of-fold"
                    if value == "coarse_grouped_5fold_oof"
                    else "Coarse-trained fine-geometry holdout"
                ),
            )
            plot_data = predictions[predictions["evaluation"] == eval_label]
            left, right = st.columns(2)
            with left:
                scatter = px.scatter(
                    plot_data,
                    x="actual_stress_mpa",
                    y="predicted_stress_mpa",
                    color="model",
                    hover_data=[
                        "candidate_id",
                        "geometry_hash",
                        "load_case",
                        "mesh_fidelity",
                        "fold_id",
                    ],
                    labels={
                        "actual_stress_mpa": "Actual peak stress (MPa)",
                        "predicted_stress_mpa": "Predicted peak stress (MPa)",
                    },
                    title="Genuine row-level prediction versus FEA",
                )
                scatter.add_shape(
                    type="line",
                    x0=0,
                    y0=0,
                    x1=2000,
                    y1=2000,
                    line={"dash": "dash", "color": "#475569"},
                )
                st.plotly_chart(scatter, width="stretch")
            with right:
                st.plotly_chart(
                    px.histogram(
                        plot_data,
                        x="residual_mpa",
                        color="model",
                        nbins=24,
                        labels={"residual_mpa": "FEA minus prediction (MPa)"},
                        title="Genuine prediction residual distribution",
                    ),
                    width="stretch",
                )
        analytics_diagnostics["phase4_ml_evaluation"] = p4
    else:
        st.info("Phase 4 model-evaluation data is not available in this checkout.")

    phase3_model = root / "models/phase3_surrogate.json"
    with st.expander("Historical Phase 3 evaluation", expanded=False):
        if phase3_model.exists():
            md = read(phase3_model)
            mlp_stress = md.get("held_out_metrics", {}).get("max_von_mises_mpa", {})
            cols = st.columns(4)
            cols[0].metric("Historical samples", md.get("sample_count", "N/A"))
            cols[1].metric("Geometry groups", md.get("geometry_group_count", "N/A"))
            cols[2].metric(
                "MLP stress MAE", f"{mlp_stress.get('MAE', float('nan')):.2f} MPa"
            )
            cols[3].metric("MLP stress R²", f"{mlp_stress.get('R2', float('nan')):.3f}")
            st.caption(
                "This is Phase 3 historical model data (24 rows, 12 geometry groups); "
                "it is not the Phase 4 evaluation and is not used for current screening."
            )
            phase3_predictions = root / "models/phase3_surrogate.test.csv"
            if phase3_predictions.exists():
                historical_rows = pd.read_csv(phase3_predictions)
                if {"max_von_mises_mpa_actual", "max_von_mises_mpa_predicted"}.issubset(
                    historical_rows.columns
                ):
                    st.plotly_chart(
                        px.scatter(
                            historical_rows,
                            x="max_von_mises_mpa_actual",
                            y="max_von_mises_mpa_predicted",
                            labels={
                                "max_von_mises_mpa_actual": "Actual stress (MPa)",
                                "max_von_mises_mpa_predicted": "Predicted stress (MPa)",
                            },
                            title="Historical Phase 3 MLP test set",
                        ),
                        width="stretch",
                    )
            analytics_diagnostics["phase3_model_metadata"] = md
        else:
            st.info("Historical Phase 3 model metadata is unavailable.")

    multifidelity = root / "data/phase2/multifidelity.json"
    with st.expander("Historical Phase 2 multifidelity evaluation", expanded=False):
        if multifidelity.exists():
            multi_data = read(multifidelity)
            holdout_metrics = st.columns(3)
            holdout_metrics[0].metric(
                "Held-out fine cases", multi_data.get("held_out_fine_cases", "N/A")
            )
            holdout_metrics[1].metric(
                "Held-out geometry groups",
                len(multi_data.get("held_out_geometry_groups", [])),
            )
            holdout_metrics[2].metric(
                "Eligible for optimization",
                "No"
                if not multi_data.get("selected_for_optimization")
                else "Historical only",
            )
            coarse = multi_data.get("coarse_prediction_on_fine", {})
            corrected = multi_data.get("additive_ridge_correction_on_fine", {})
            holdout_rows = [
                {
                    "Response": response.replace("_", " ").title(),
                    "Statistic": statistic,
                    "Coarse model": coarse.get(response, {}).get(statistic),
                    "Ridge-corrected model": corrected.get(response, {}).get(statistic),
                }
                for response in ("max_von_mises_mpa", "max_displacement_mm")
                for statistic in ("MAE", "RMSE", "R2")
            ]
            st.dataframe(pd.DataFrame(holdout_rows), hide_index=True, width="stretch")
            st.caption(
                "Two held-out geometry groups only; both variants remain exploratory and are not used for constraint enforcement."
            )
            analytics_diagnostics["phase2_multifidelity"] = multi_data
        else:
            st.info("Historical Phase 2 multifidelity metrics are unavailable.")
    if analytics_diagnostics:
        advanced_diagnostics(analytics_diagnostics)
