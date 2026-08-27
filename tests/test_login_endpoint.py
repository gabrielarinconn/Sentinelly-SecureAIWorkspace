"""Smoke test del endpoint HTTP mínimo de login (Fase 4). Contra PostgreSQL real."""

from fastapi.testclient import TestClient

from backend.presentation.api import app

client = TestClient(app)


def test_login_endpoint_returns_a_jwt_for_valid_credentials():
    response = client.post("/auth/login", json={"email": "bob@sentinel.dev", "password": "DemoPass123!"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2


def test_login_endpoint_rejects_wrong_password():
    response = client.post("/auth/login", json={"email": "bob@sentinel.dev", "password": "wrong"})
    assert response.status_code == 401


def test_login_endpoint_rejects_unknown_email():
    response = client.post("/auth/login", json={"email": "nobody@sentinel.dev", "password": "DemoPass123!"})
    assert response.status_code == 401
