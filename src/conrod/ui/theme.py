"""RodLab page-level typography, spacing and responsive layout."""

PAGE_CSS = """<style>
:root{--rod-navy:#12283f;--rod-teal:#0f766e;--rod-bg:#f5f8fc;--rod-ink:#24364b;--rod-muted:#64748b;--rod-border:#dce4ec;--rod-success:#16835d;--rod-warning:#b7791f;--rod-danger:#c2413b}
[data-testid="stAppViewContainer"]{background:var(--rod-bg);color:var(--rod-ink)}
.block-container{max-width:1380px;padding:4rem 1.5rem 3rem}h1,h2,h3{color:var(--rod-navy);letter-spacing:-.025em;line-height:1.18}
.rodlab-brand{display:flex;align-items:center;gap:.7rem;color:var(--rod-navy);margin:.05rem 0 .25rem;font-size:1rem;line-height:1.2}.rodlab-brand strong{font-size:1.12rem}.rodlab-brand span{font-size:.68rem;font-weight:700;letter-spacing:.095em;color:var(--rod-muted)}
[data-testid="stMetric"]{box-sizing:border-box;min-width:0;height:100%;border:1px solid var(--rod-border);border-radius:10px;padding:.72rem .85rem;background:#fff;box-shadow:0 1px 2px #12283f08}
[data-testid="stMetricLabel"]{white-space:normal!important;overflow-wrap:anywhere;font-size:.8rem;line-height:1.25;color:var(--rod-muted)}
[data-testid="stMetricValue"]{white-space:normal!important;overflow-wrap:anywhere;word-break:normal;font-size:clamp(1.18rem,1.7vw,1.75rem);line-height:1.16;color:var(--rod-navy)}
[data-testid="stMetricValue"] [data-testid="stMarkdownContainer"],[data-testid="stMetricValue"] p{white-space:normal!important;overflow:visible!important;overflow-wrap:anywhere;text-overflow:clip!important}
[data-testid="stMetricDelta"]{white-space:normal!important;overflow-wrap:anywhere}
[data-testid="stSidebar"]{border-right:1px solid var(--rod-border);background:#fff}
[data-testid="stSidebarNav"] a{border-radius:7px}[data-testid="stSidebarNav"] a[aria-current="page"]{background:#e7f3f2;color:var(--rod-teal);font-weight:650}
.stButton>button,.stDownloadButton>button{border-radius:8px;min-height:2.35rem;border-color:var(--rod-border)}div[data-testid="stCaptionContainer"]{line-height:1.5;color:var(--rod-muted)}
[data-testid="stHorizontalBlock"]{gap:.75rem}
@media(max-width:900px){.block-container{padding:4rem 1rem 2.25rem}[data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.6rem}[data-testid="stColumn"]{min-width:min(100%,14rem)!important;flex:1 1 14rem}[data-testid="stMetric"]{padding:.65rem .72rem}}
@media(max-width:560px){.block-container{padding:4rem .8rem 1.8rem}h1{font-size:1.65rem!important}h2{font-size:1.32rem!important}[data-testid="stHorizontalBlock"]{gap:.42rem}[data-testid="stColumn"]{width:calc(50% - .24rem)!important;min-width:calc(50% - .24rem)!important;max-width:calc(50% - .24rem)!important;flex:1 1 calc(50% - .24rem)!important}[data-testid="stMetricValue"]{font-size:1.32rem}[data-testid="stMetric"]{padding:.56rem .62rem}}
</style>"""


def configure_page(st):
    st.set_page_config(
        page_title="RodLab | Phase 4 engineering workspace",
        page_icon="⚙",
        layout="wide",
        initial_sidebar_state="auto",
    )
    sidebar_navigation = """<script>
if (!window.__rodlabMobileNavigation) {
  window.__rodlabMobileNavigation = true;
  document.addEventListener("click", (event) => {
    const navigation = document.querySelector('[data-testid="stSidebarNav"]');
    const link = event.target.closest('[data-testid="stSidebarNav"] a');
    if (!navigation || !link || window.innerWidth > 768) return;
    window.setTimeout(() => {
      const sidebar = document.querySelector('[data-testid="stSidebar"]');
      const collapse = sidebar?.querySelector('button[aria-label="Collapse sidebar"]');
      if (collapse && sidebar.dataset.collapsed !== "true") collapse.click();
    }, 250);
  }, true);
}
</script>"""
    st.html(PAGE_CSS + sidebar_navigation, unsafe_allow_javascript=True)
