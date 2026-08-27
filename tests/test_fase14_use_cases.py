"""Fase 14: ListChannels (GET /channels) y GetCurrentUser (GET /users/me) — casos de uso
delgados sobre la vista de conversaciones (Fase 9) y rw_users."""

import pytest
from fastapi.testclient import TestClient

from backend.presentation.api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "DemoPass123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_list_channels_returns_only_the_actors_own_conversations(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")
    response = client.get("/channels", headers={"Authorization": f"Bearer {alice_token}"})
    assert response.status_code == 200
    names = [c["channel_name"] for c in response.json()]
    assert names == ["general"]


def test_get_current_user_returns_the_authenticated_users_own_profile(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.get("/users/me", headers={"Authorization": f"Bearer {bob_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "bob@sentinel.dev"
    assert body["full_name"] == "Bob Chen"
    assert body["role_title"] == "Engineering Lead"


def test_endpoints_require_authentication(client: TestClient):
    assert client.get("/channels").status_code in (401, 422)
    assert client.get("/users/me").status_code in (401, 422)
