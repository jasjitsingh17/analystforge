# AnalystForge Deployment Preparation

This document is the pre-deployment checklist for Stage 11. The application is already structured as a single FastAPI service that serves both the browser frontend and API endpoints.

## Production command

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

## Health check

```text
GET /api/health
```

Expected response:

```json
{"status":"healthy"}
```

## Option A — Render

The repository includes `render.yaml` with:

- Python web-service runtime
- `pip install -r requirements.txt` build step
- Uvicorn start command
- `/api/health` health check

Stage 11 can connect the GitHub repository to Render and create the public deployment.

## Option B — Docker

Build locally:

```bash
docker build -t analystforge .
```

Run locally:

```bash
docker run --rm -p 8000:8000 -e PORT=8000 analystforge
```

Then open:

```text
http://127.0.0.1:8000/
```

## Pre-deployment checks

Before publishing:

1. Run the full test suite.
2. Confirm the homepage loads at `/`.
3. Confirm `/api/health` returns HTTP 200.
4. Confirm `/docs` loads.
5. Test all three analytical workflows.
6. Download the DCF workbook.
7. Download the M&A merger model.
8. Download the equity-research workbook.
9. Open the equity-research note.
10. Check the sidebar, gallery and mobile/responsive states.
11. Confirm no local absolute file paths appear in committed source code.
12. Confirm no API keys, credentials or private files are committed.

## Runtime files

Generated Excel outputs are runtime artifacts and should not be committed to Git. The included `.gitignore` excludes generated files under `outputs/`.

For a portfolio deployment, generated files can remain ephemeral. Persistent cloud storage is unnecessary unless AnalystForge later becomes a multi-user production application.

## Environment variables

AnalystForge currently uses controlled sample data and does not require external credentials. `.env.example` therefore contains only the optional `PORT` variable.

If live-data integrations are added later, credentials should be stored as deployment-platform environment variables and never committed to GitHub.

## Public-domain setup

Stage 11 should complete the deployment first and then connect the chosen custom domain. Recommended long-term structures include:

```text
analystforgebyjasjit.com
```

or, if a broader personal portfolio is created later:

```text
jasjitbhatia.com/analystforge
```

Do not purchase or configure a domain until the hosted service is working correctly on its platform-provided URL.
