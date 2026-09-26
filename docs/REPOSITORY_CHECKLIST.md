# GitHub Repository Checklist

## Keep in the public repository

- `backend/`
- `frontend/`
- `tests/`
- `docs/`
- `requirements.txt`
- `pytest.ini`
- `README.md`
- `.gitignore`
- `.dockerignore`
- `Dockerfile`
- `Procfile`
- `render.yaml`
- `.github/workflows/tests.yml`

## Keep local / do not publish

- `.venv/`
- `archive/`
- `backup_before_final_site/`
- `__pycache__/`
- `.pytest_cache/`
- generated `.xlsx` files
- ad-hoc screenshots that contain browser chrome, desktop apps or personal local paths
- secrets, `.env` files or API keys

## Recommended GitHub repository settings

**Repository name**

```text
analystforge
```

**Description**

```text
Financial-analysis workbench for DCF valuation, M&A execution and equity-research workflows with Python engines, FastAPI, interactive dashboards and Excel outputs.
```

**Topics**

```text
finance
investment-banking
valuation
dcf
mergers-and-acquisitions
equity-research
fastapi
python
excel
financial-modeling
pytest
portfolio-project
```

**Homepage**

Leave blank until Stage 11 produces the live public URL, then add that URL to the repository About section.

## Before the first public push

Run:

```bash
python -m pytest -v
```

Then check what Git will publish:

```bash
git status
git ls-files
```

Review the output before making the repository public.
