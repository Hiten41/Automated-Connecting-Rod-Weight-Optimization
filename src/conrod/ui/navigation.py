"""Native Streamlit navigation structure for the Phase 4 workspace."""

PAGE_GROUPS = (
    ("OVERVIEW", (("dashboard", "Dashboard", "01"),)),
    (
        "DESIGN",
        (
            ("design_studio", "Design Studio", "02"),
            ("design_space_explorer", "Design Space Explorer", "03"),
            ("legacy_geometry_editor", "Legacy Geometry Editor", "04"),
        ),
    ),
    (
        "LOADS AND SIMULATION",
        (
            ("engine_loading", "Engine Loading", "05"),
            ("simulation", "Simulation", "06"),
        ),
    ),
    (
        "ANALYSIS",
        (
            ("results_comparison", "Results & Comparison", "07"),
            ("model_analytics", "Model Analytics", "08"),
            ("optimization_feasibility", "Optimization & Feasibility", "09"),
        ),
    ),
    ("PROJECT", (("reports_downloads", "Reports & Downloads", "10"),)),
)


def build_navigation(st):
    """Build real page navigation, grouped for desktop and mobile use."""
    pages = {
        group: [
            st.Page(
                f"pages/{path}.py",
                title=title,
                url_path=path.replace("_", "-"),
                default=path == "dashboard",
            )
            for path, title, _order in entries
        ]
        for group, entries in PAGE_GROUPS
    }
    return st.navigation(pages, position="sidebar", expanded=False)
