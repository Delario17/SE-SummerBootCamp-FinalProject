"""Tests for web dashboard."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.web.app import app
    return TestClient(app)


def test_dashboard_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_api_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_api_history(client):
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_audit(client):
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)