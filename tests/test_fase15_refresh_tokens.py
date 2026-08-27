"""Fase 15 DoD: login emite access+refresh; refresh rota (A -> revoke A -> create B);
logout revoca; un refresh token ya revocado que se reutiliza -> DENY (reuse detection)."""

import pytest
from fastapi.testclient import TestClient

from backend.presentation.api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str = "bob@sentinel.dev") -> dict:
    response = client.post("/auth/login", json={"email": email, "password": "DemoPass123!"})
    assert response.status_code == 200
    return response.json()


def test_login_issues_both_an_access_and_a_refresh_token(client: TestClient):
    tokens = _login(client)
    assert tokens["access_token"].count(".") == 2
    assert len(tokens["refresh_token"]) > 20
    assert tokens["refresh_token"] != tokens["access_token"]


def test_refresh_rotates_the_token_and_issues_a_new_access_token(client: TestClient):
    first = _login(client)
    response = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert second["access_token"] != first["access_token"]


def test_reusing_an_already_rotated_refresh_token_is_denied(client: TestClient):
    first = _login(client)
    # Rota una vez: A queda revocado, se emite B.
    client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})

    # Reutilizar A (ya revocado) -> DENY explícito.
    replay = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401


def test_reuse_detection_revokes_the_entire_chain_including_the_latest_token(client: TestClient):
    """El token robado (A) se reutiliza después de que la víctima ya rotó a B — la respuesta
    de seguridad revoca TODO lo activo del usuario, incluido B, no solo A."""
    first = _login(client)
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).json()

    # Reuse de A detectado -> revoca la cadena completa, incluyendo B.
    client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})

    # B, que era válido hace un segundo, ahora también está revocado.
    response_with_b = client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert response_with_b.status_code == 401


def test_logout_revokes_the_refresh_token(client: TestClient):
    tokens = _login(client)
    logout_response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 204

    refresh_after_logout = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_after_logout.status_code == 401


def test_refresh_with_an_unknown_token_is_denied(client: TestClient):
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-refresh-token"})
    assert response.status_code == 401


def test_logout_with_an_unknown_token_does_not_error(client: TestClient):
    response = client.post("/auth/logout", json={"refresh_token": "not-a-real-refresh-token"})
    assert response.status_code == 204
