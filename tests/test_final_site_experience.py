"""Regression tests for the final public website experience."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
SHOWCASE = ROOT / "frontend" / "showcase"


def test_homepage_is_present_and_default_shell_exists():
    assert 'id="home-view"' in HTML
    assert 'id="home"' in HTML


def test_homepage_leads_with_platform_introduction():
    assert "From assumptions to analyst-ready deliverables." in HTML
    assert "valuation, transaction execution and equity research" in HTML


def test_usage_section_exists():
    assert 'id="usage-section"' in HTML
    assert "For students" in HTML
    assert "For professionals" in HTML


def test_usage_section_uses_two_columns():
    assert 'class="usage-columns"' in HTML
    assert HTML.count('class="usage-column"') == 2


def test_usage_columns_have_vertical_divider_styling():
    assert ".usage-columns::before" in CSS
    assert "left:50%" in CSS


def test_showcase_section_exists_after_usage():
    assert 'id="showcase-section"' in HTML
    assert HTML.index('id="usage-section"') < HTML.index('id="showcase-section"')


def test_showcase_has_horizontal_rail():
    assert 'id="home-showcase-rail"' in HTML
    assert ".showcase-rail" in CSS
    assert "scroll-snap-type:x mandatory" in CSS


def test_showcase_has_next_and_previous_controls():
    assert 'data-scroll-rail="home-showcase-rail" data-direction="-1"' in HTML
    assert 'data-scroll-rail="home-showcase-rail" data-direction="1"' in HTML


def test_creator_section_comes_after_showcase():
    assert 'id="creator-section"' in HTML
    assert HTML.index('id="showcase-section"') < HTML.index('id="creator-section"')


def test_creator_name_is_present():
    assert "Jasjit Singh Bhatia" in HTML


def test_creator_intro_is_present_before_socials():
    assert "Warwick Business School graduate" in HTML
    assert "Tesco PLC" in HTML
    assert "RACDEE Consulting" in HTML
    assert "RSM US LLP" in HTML
    assert "FA Investment &amp; Insurance Services" in HTML
    assert HTML.index("Warwick Business School graduate") < HTML.index('class="social-links"')


def test_creator_intro_uses_cloud_treatment():
    assert 'class="creator-cloud"' in HTML
    assert ".creator-cloud::before" in CSS


def test_linkedin_icon_is_clickable():
    assert 'href="https://www.linkedin.com/in/jasjitsinghbhatia/"' in HTML
    assert 'aria-label="LinkedIn"' in HTML


def test_instagram_icon_is_clickable():
    assert 'href="https://www.instagram.com/jasjitsingh_17/"' in HTML
    assert 'aria-label="Instagram"' in HTML


def test_email_icon_is_clickable():
    assert 'href="mailto:jasjitsingh170@gmail.com"' in HTML
    assert 'aria-label="Email Jasjit"' in HTML


def test_social_links_use_icons_not_visible_urls():
    assert HTML.count('class="social-icon"') == 3
    assert HTML.count("<svg") >= 3
    assert ">https://www.linkedin.com" not in HTML
    assert ">https://www.instagram.com" not in HTML


def test_expandable_sidebar_exists():
    assert 'id="tool-sidebar"' in HTML
    assert 'id="menu-toggle"' in HTML
    assert 'aria-expanded="false"' in HTML


def test_sidebar_is_hidden_off_canvas_by_default():
    assert "transform: translateX(-104%)" in CSS
    assert ".tool-sidebar.is-open" in CSS


def test_sidebar_contains_all_three_tools():
    assert '>Valuation</button>' in HTML
    assert '>M&amp;A Execution</button>' in HTML
    assert '>Equity Research</button>' in HTML


def test_sidebar_preserves_workflow_tab_ids():
    for tab_id in ("tab-ib", "tab-ma", "tab-er"):
        assert f'id="{tab_id}"' in HTML


def test_sales_and_trading_remains_removed():
    assert "Sales &amp; Trading" not in HTML
    assert 'id="tab-st"' not in HTML
    assert 'id="panel-st"' not in HTML


def test_home_and_tool_routing_exist():
    for route in ("#home", "#valuation", "#ma-execution", "#equity-research"):
        assert route in JS


def test_smooth_view_transition_has_modern_and_fallback_paths():
    assert "document.startViewTransition" in JS
    assert ".animate([" in JS
    assert "cubic-bezier(.2,.8,.2,1)" in JS


def test_sidebar_open_close_logic_exists():
    assert "function setSidebar(open)" in JS
    assert 'classList.toggle("is-open", open)' in JS


def test_escape_closes_navigation():
    assert 'event.key === "Escape"' in JS


def test_tool_pages_have_how_it_works_sections():
    assert HTML.count('class="tool-guide"') == 3
    assert HTML.count("From assumptions to analyst-ready output") == 3


def test_each_tool_has_three_preview_cards():
    assert HTML.count('class="tool-preview-card screenshot-open"') == 9


def test_each_core_form_is_preserved():
    for form_id in ("dcf-form", "ma-form", "er-form"):
        assert f'id="{form_id}"' in HTML


def test_download_actions_are_preserved():
    for element_id in ("download-excel", "download-ma-excel", "download-er-excel", "open-er-report"):
        assert f'id="{element_id}"' in HTML


def test_existing_api_integrations_are_preserved():
    for endpoint in ("/api/dcf", "/api/ma-execution", "/api/equity-research"):
        assert f'fetch("{endpoint}"' in JS


def test_existing_download_integrations_are_preserved():
    for endpoint in ("/api/dcf/excel", "/api/ma-execution/excel", "/api/equity-research/excel"):
        assert endpoint in JS


def test_research_note_integration_is_preserved():
    assert "/api/equity-research/report" in JS


def test_tool_jump_controls_exist():
    for target in ("dcf-form", "ma-form", "er-form"):
        assert f'data-scroll-target="{target}"' in HTML
    assert 'document.querySelectorAll(".tool-jump")' in JS


def test_lightbox_support_exists():
    assert 'id="image-lightbox"' in HTML
    assert "function openLightbox" in JS
    assert ".image-lightbox.is-open" in CSS


def test_showcase_assets_exist():
    expected = {
        "valuation-input.webp", "valuation-dashboard.webp", "valuation-excel.webp",
        "ma-input.webp", "ma-dashboard.webp", "ma-excel.webp",
        "er-input.webp", "er-dashboard.webp", "er-report.webp",
    }
    assert expected <= {p.name for p in SHOWCASE.iterdir() if p.is_file()}


def test_showcase_images_are_local_static_assets():
    assert "https://" not in "\n".join(line for line in HTML.splitlines() if "/static/showcase/" in line)
    assert HTML.count("/static/showcase/") >= 18


def test_homepage_is_responsive():
    assert "@media (max-width: 1050px)" in CSS
    assert "@media (max-width: 760px)" in CSS
    assert "@media (max-width: 480px)" in CSS


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion: reduce" in CSS


def test_sidebar_is_accessible():
    assert 'aria-controls="tool-sidebar"' in HTML
    assert 'aria-label="Tool navigation"' in HTML


def test_screenshot_cards_are_keyboard_accessible():
    assert 'tabindex="0" role="button"' in HTML
    assert 'event.key === "Enter" || event.key === " "' in JS


def test_platform_footer_is_preserved():
    assert 'class="app-footer"' in HTML
    assert "Portfolio-grade financial analysis workflows" in HTML


def test_public_site_has_no_external_frontend_framework_dependency():
    assert "cdn.jsdelivr.net" not in HTML
    assert "unpkg.com" not in HTML
    assert "fonts.googleapis.com" not in HTML


def test_creator_socials_follow_intro_requirement():
    cloud = HTML.index('class="creator-cloud"')
    socials = HTML.index('class="social-links"')
    assert cloud < socials


def test_homepage_section_order_matches_brief():
    hero = HTML.index('id="home"')
    usage = HTML.index('id="usage-section"')
    showcase = HTML.index('id="showcase-section"')
    creator = HTML.index('id="creator-section"')
    assert hero < usage < showcase < creator
