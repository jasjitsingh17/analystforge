"""Regression tests for the AnalystForge interactive portfolio experience."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
BRAND = ROOT / "frontend" / "brand"
SHOWCASE = ROOT / "frontend" / "showcase"


def test_analystforge_is_primary_brand():
    assert "AnalystForge" in HTML
    assert "AnalystForge | Financial Analyst Automation Platform" in HTML


def test_final_logo_is_used_in_header():
    assert 'class="brand-logo"' in HTML
    assert '/static/brand/analystforge-logo.png' in HTML


def test_final_logo_is_used_in_hero():
    assert 'class="hero-logo"' in HTML
    assert HTML.count('/static/brand/analystforge-logo.png') >= 2


def test_brand_assets_exist():
    assert (BRAND / "analystforge-logo.png").is_file()
    assert (BRAND / "analystforge-mark.png").is_file()
    assert (BRAND / "analystforge-logo.png").stat().st_size > 50_000


def test_favicon_uses_brand_mark():
    assert 'href="/static/brand/analystforge-mark.png"' in HTML


def test_hero_has_new_positioning():
    assert "From assumptions to analyst-ready deliverables." in HTML
    assert "transparent workbench" in HTML


def test_hero_contains_open_workbench_action():
    assert 'id="hero-explore-tools"' in HTML
    assert "Open the workbench" in HTML


def test_homepage_has_interactive_workflow_stage():
    assert 'id="hero-stage"' in HTML
    assert HTML.count('class="hero-flow-card') == 3
    assert 'data-hero-tool="panel-ib"' in HTML
    assert 'data-hero-tool="panel-ma"' in HTML
    assert 'data-hero-tool="panel-er"' in HTML


def test_homepage_has_morphing_visual_layer():
    assert 'class="hero-morph hero-morph--one"' in HTML
    assert '@keyframes afMorph' in CSS


def test_pointer_driven_hero_interaction_exists():
    assert 'afHero.addEventListener("pointermove"' in JS
    assert '--af-glow-x' in JS
    assert '--tilt-x' in JS


def test_hero_workflows_auto_cycle():
    assert "setActiveHeroFlow" in JS
    assert "3200" in JS


def test_platform_overview_section_exists():
    assert 'id="platform-section"' in HTML
    assert "Three workflows. One analytical system." in HTML


def test_platform_has_three_workflow_cards():
    assert HTML.count('class="workflow-card"') == 3
    for text in ("Build the investment case.", "Structure the transaction.", "Review the earnings story."):
        assert text in HTML


def test_workflow_cards_open_real_tools():
    for panel in ("panel-ib", "panel-ma", "panel-er"):
        assert f'data-open-tool="{panel}"' in HTML


def test_student_professional_split_is_preserved():
    assert 'id="usage-section"' in HTML
    assert "For students" in HTML
    assert "For professionals" in HTML
    assert ".usage-columns::before" in CSS


def test_transparent_pipeline_section_exists():
    assert 'id="process-section"' in HTML
    for text in ("Structure inputs", "Run the engine", "Review visually", "Export"):
        assert text in HTML


def test_showcase_explicitly_uses_authentic_captures():
    assert "AUTHENTIC WORKFLOW OUTPUTS" in HTML
    assert "actual controlled-sample" in HTML.lower()
    assert "ACTUAL WORKFLOW CAPTURE" in HTML


def test_showcase_assets_are_local():
    names = {p.name for p in SHOWCASE.iterdir() if p.is_file()}
    expected = {
        "valuation-input.webp", "valuation-dashboard.webp", "valuation-excel.webp",
        "ma-input.webp", "ma-dashboard.webp", "ma-excel.webp",
        "er-input.webp", "er-dashboard.webp", "er-report.webp",
    }
    assert expected <= names


def test_showcase_has_no_external_image_urls():
    showcase_lines = "\n".join(line for line in HTML.splitlines() if "showcase/" in line)
    assert "http://" not in showcase_lines
    assert "https://" not in showcase_lines


def test_showcase_has_lightbox_and_horizontal_scroll():
    assert 'id="home-showcase-rail"' in HTML
    assert 'id="image-lightbox"' in HTML
    assert "scroll-snap-type:x mandatory" in CSS


def test_creator_is_described_as_wbs_graduate():
    assert "Warwick Business School graduate" in HTML
    assert "MSc Business &amp; Finance" in HTML
    assert "candidate at Warwick Business School" not in HTML


def test_creator_intro_includes_tesco_experience():
    assert "Tesco PLC" in HTML
    assert "FX and interest-rate exposure" in HTML


def test_creator_intro_includes_racdee_experience():
    assert "RACDEE Consulting" in HTML
    assert "variance analysis" in HTML


def test_creator_intro_includes_rsm_experience():
    assert "RSM US LLP" in HTML
    assert "audit work" in HTML


def test_creator_intro_includes_investment_services_experience():
    assert "FA Investment &amp; Insurance Services" in HTML
    assert "portfolio, market and investment-analysis support" in HTML


def test_creator_intro_includes_technical_skills():
    for text in ("Advanced Excel", "Bloomberg Terminal", "BQL", "Python", "FastAPI", "pytest", "HTML/CSS/JavaScript", "DCF valuation"):
        assert text in HTML


def test_creator_social_icons_follow_intro():
    intro = HTML.index("I’m Jasjit")
    socials = HTML.index('class="social-links"')
    assert intro < socials


def test_creator_social_links_are_correct():
    assert 'href="https://www.linkedin.com/in/jasjitsinghbhatia/"' in HTML
    assert 'href="https://www.instagram.com/jasjitsingh_17/"' in HTML
    assert 'href="mailto:jasjitsingh170@gmail.com"' in HTML


def test_sidebar_is_still_hidden_expandable_navigation():
    assert 'id="tool-sidebar"' in HTML
    assert 'id="menu-toggle"' in HTML
    assert "transform: translateX(-104%)" in CSS
    assert ".tool-sidebar.is-open" in CSS


def test_sidebar_contains_descriptive_tool_summaries():
    assert "DCF • Sensitivity • Excel" in HTML
    assert "Deal model • A/D • Excel" in HTML
    assert "Earnings • Note • Excel" in HTML


def test_each_tool_page_has_extra_context_facts():
    assert HTML.count('class="tool-fact-row"') == 3
    for text in ("DCF, WACC, terminal value", "Purchase price, sources &amp; uses", "Earnings vs consensus"):
        assert text in HTML


def test_existing_financial_forms_are_preserved():
    for form_id in ("dcf-form", "ma-form", "er-form"):
        assert f'id="{form_id}"' in HTML


def test_existing_downloads_are_preserved():
    for element_id in ("download-excel", "download-ma-excel", "download-er-excel", "open-er-report"):
        assert f'id="{element_id}"' in HTML


def test_existing_api_calls_are_preserved():
    for endpoint in ("/api/dcf", "/api/ma-execution", "/api/equity-research"):
        assert endpoint in JS


def test_view_transition_and_fallback_are_preserved():
    assert "document.startViewTransition" in JS
    assert ".animate([" in JS
    assert "::view-transition-new(root)" in CSS


def test_scroll_reveal_is_progressive_enhancement():
    assert "IntersectionObserver" in JS
    assert "js-reveal-ready" in JS
    assert ".reveal { opacity:1" in CSS


def test_scroll_progress_exists():
    assert 'id="scroll-progress"' in HTML
    assert "--page-progress" in JS


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion:reduce" in CSS or "prefers-reduced-motion: reduce" in CSS
    assert "reduceMotion" in JS


def test_public_site_uses_no_external_frontend_framework():
    for host in ("cdn.jsdelivr.net", "unpkg.com", "fonts.googleapis.com"):
        assert host not in HTML


def test_sales_and_trading_is_not_reintroduced():
    assert "Sales &amp; Trading" not in HTML
    assert 'id="tab-st"' not in HTML
    assert 'id="panel-st"' not in HTML
