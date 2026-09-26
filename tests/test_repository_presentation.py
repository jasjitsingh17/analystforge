from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_readme_exists():
    assert (ROOT / "README.md").is_file()


def test_readme_brands_project_as_analystforge():
    text = read("README.md")
    assert "AnalystForge" in text
    assert "Valuation" in text
    assert "M&A Execution" in text
    assert "Equity Research" in text


def test_readme_uses_logo_asset():
    assert "frontend/brand/analystforge-logo.png" in read("README.md")


def test_readme_has_architecture_diagram():
    text = read("README.md")
    assert "```mermaid" in text
    assert "FastAPI" in text


def test_readme_has_screenshots():
    text = read("README.md")
    assert "valuation-dashboard.webp" in text
    assert "ma-dashboard.webp" in text
    assert "er-report.webp" in text


def test_readme_has_setup_and_testing():
    text = read("README.md")
    assert "## Local setup" in text
    assert "python -m pytest -v" in text


def test_readme_discloses_controlled_data():
    text = read("README.md").lower()
    assert "controlled" in text
    assert "not" in text and "investment advice" in text


def test_gitignore_excludes_virtualenv_and_generated_outputs():
    text = read(".gitignore")
    assert ".venv/" in text
    assert "outputs/*" in text
    assert "archive/" in text
    assert "*.xlsx" in text


def test_dockerfile_starts_fastapi():
    text = read("Dockerfile")
    assert "uvicorn backend.main:app" in text
    assert "${PORT:-8000}" in text


def test_render_config_has_health_check():
    text = read("render.yaml")
    assert "/api/health" in text
    assert "backend.main:app" in text


def test_procfile_exists():
    text = read("Procfile")
    assert text.startswith("web:")
    assert "backend.main:app" in text


def test_github_action_runs_pytest():
    text = read(".github/workflows/tests.yml")
    assert "python -m pytest -q" in text
    assert "python-version: \"3.14\"" in text


def test_architecture_document_exists():
    text = read("docs/ARCHITECTURE.md")
    assert "Deterministic Python Engines" in text
    assert "does **not** duplicate" in text


def test_deployment_document_exists():
    text = read("docs/DEPLOYMENT.md")
    assert "Production command" in text
    assert "/api/health" in text


def test_repository_checklist_exists():
    text = read("docs/REPOSITORY_CHECKLIST.md")
    assert "analystforge" in text
    assert "Keep local / do not publish" in text


def test_no_fake_live_demo_link_in_readme():
    text = read("README.md").lower()
    assert "your-live-demo" not in text
    assert "example.com" not in text


def test_creator_links_present():
    text = read("README.md")
    assert "linkedin.com/in/jasjitsinghbhatia" in text
    assert "instagram.com/jasjitsingh_17" in text
    assert "mailto:jasjitsingh170@gmail.com" in text
