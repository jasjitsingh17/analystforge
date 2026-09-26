"""Health and frontend-serving tests."""

from fastapi.testclient import TestClient

from backend.main import APP_NAME, app

client = TestClient(app)


def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_root_serves_frontend_html():
    response = client.get("/")
    assert response.headers["content-type"].startswith("text/html")
    assert APP_NAME in response.text
    assert 'id="dcf-form"' in response.text


def test_stylesheet_is_reachable():
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_javascript_is_reachable():
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert 'fetch("/api/dcf"' in response.text


def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_expected_status():
    response = client.get("/api/health")
    assert response.json() == {"status": "healthy"}
