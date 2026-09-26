"""Stage 9 regression tests for the unified professional website shell."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")


def test_product_title_is_preserved():
    assert "Financial Analyst Automation Platform" in HTML


def test_professional_meta_description_exists():
    assert 'name="description"' in HTML
    assert "valuation, M&amp;A execution and equity research" not in HTML  # attribute is raw '&'
    assert "valuation, M&A execution and equity research" in HTML


def test_brand_workbench_shell_exists():
    assert 'class="brand-block"' in HTML
    assert 'class="brand-mark"' in HTML
    assert "ANALYST WORKBENCH" in HTML


def test_header_describes_three_core_workflows():
    assert "Valuation, transaction execution and equity research workflows" in HTML


def test_header_capability_chips_exist():
    for text in ("3 Workflows", "Python Engines", "Excel Outputs"):
        assert text in HTML


def test_navigation_uses_final_portfolio_labels():
    assert '>Valuation</button>' in HTML
    assert '>M&amp;A Execution</button>' in HTML
    assert '>Equity Research</button>' in HTML


def test_navigation_preserves_existing_tab_ids():
    for tab_id in ("tab-ib", "tab-ma", "tab-er"):
        assert f'id="{tab_id}"' in HTML


def test_sales_and_trading_is_not_reintroduced():
    assert 'id="tab-st"' not in HTML
    assert 'id="panel-st"' not in HTML
    assert "Sales &amp; Trading" not in HTML


def test_valuation_panel_keeps_investment_banking_domain_reference():
    assert 'data-domain="Investment Banking"' in HTML
    assert 'id="panel-ib"' in HTML


def test_each_workflow_has_a_professional_kicker():
    for text in ("VALUATION WORKFLOW", "TRANSACTION WORKFLOW", "RESEARCH WORKFLOW"):
        assert text in HTML


def test_each_workflow_keeps_python_engine_badge():
    for text in ("Python DCF Engine", "Python M&amp;A Engine", "Python ER Engine"):
        assert text in HTML


def test_each_workflow_has_state_chip():
    for text in ("Deterministic model", "Deal execution", "Analyst workflow"):
        assert text in HTML


def test_all_core_forms_are_preserved():
    for form_id in ("dcf-form", "ma-form", "er-form"):
        assert f'id="{form_id}"' in HTML


def test_all_primary_actions_are_preserved():
    for text in ("Run DCF Valuation", "Run Deal Analysis", "Run Earnings Review"):
        assert text in HTML


def test_download_and_research_outputs_are_preserved():
    for element_id in ("download-excel", "download-ma-excel", "download-er-excel", "open-er-report"):
        assert f'id="{element_id}"' in HTML


def test_footer_exists():
    assert 'class="app-footer"' in HTML
    assert "Portfolio-grade financial analysis workflows" in HTML


def test_footer_discloses_model_context():
    for text in ("Controlled sample data", "Tested Python engines", "Excel-ready outputs", "Not investment advice"):
        assert text in HTML


def test_no_external_frontend_dependencies_added():
    assert "fonts.googleapis.com" not in HTML
    assert "cdn.jsdelivr.net" not in HTML
    assert "unpkg.com" not in HTML
    assert '<script src="/static/app.js"></script>' in HTML


def test_stage9_design_system_is_present():
    assert "Stage 9 — unified institutional design system" in CSS
    assert "--shadow-xs" in CSS
    assert "--shadow-header" in CSS


def test_header_is_sticky_on_desktop():
    assert "position: sticky" in CSS
    assert "z-index: 50" in CSS


def test_cards_use_subtle_institutional_shadowing():
    assert "box-shadow: var(--shadow-xs)" in CSS
    assert ".card:hover" in CSS


def test_form_inputs_have_consistent_focus_state():
    assert "box-shadow: 0 0 0 3px rgba(31,95,191,.09)" in CSS


def test_buttons_have_professional_interaction_states():
    assert ".btn-primary:hover:not(:disabled)" in CSS
    assert ".btn-secondary:hover:not(:disabled)" in CSS


def test_tables_use_compact_institutional_headers():
    assert "text-transform: uppercase" in CSS
    assert "letter-spacing: .035em" in CSS


def test_responsive_header_breakpoint_exists():
    assert "@media (max-width: 1050px)" in CSS
    assert "@media (max-width: 760px)" in CSS


def test_mobile_actions_stack_cleanly():
    assert "@media (max-width: 480px)" in CSS
    assert ".btn-primary, .btn-secondary { width: 100%; }" in CSS


def test_reduced_motion_accessibility_is_supported():
    assert "prefers-reduced-motion: reduce" in CSS


def test_tab_keyboard_navigation_is_preserved():
    assert "ArrowRight" in JS
    assert "ArrowLeft" in JS
    assert "aria-selected" in JS


def test_all_three_engine_api_integrations_are_preserved():
    assert 'fetch("/api/dcf"' in JS
    assert 'fetch("/api/ma-execution"' in JS
    assert 'fetch("/api/equity-research"' in JS


def test_all_excel_download_integrations_are_preserved():
    assert "/api/dcf/excel" in JS
    assert "/api/ma-execution/excel" in JS
    assert "/api/equity-research/excel" in JS


def test_research_note_integration_is_preserved():
    assert "/api/equity-research/report" in JS


def test_currency_symbol_polish_is_preserved_for_ma():
    assert "maCurrencySymbol(data.currency)" in JS


def test_public_shell_remains_light_mode_only_for_consistent_portfolio_capture():
    assert 'name="color-scheme" content="light"' in HTML
