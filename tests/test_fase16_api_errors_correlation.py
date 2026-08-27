"""Fase 16 DoD: correlation ID (entra por header o se genera, siempre vuelve en la
respuesta), envelope de error uniforme, y los endpoints PATCH/DELETE /messages/{id} que
completan la API REST del plan.
"""

import pytest
from fastapi.testclient import TestClient

from backend.presentation.api import app

GENERAL_CHANNEL_ID = "10000000-0000-0000-0000-000000000001"
PRIVATE_CHANNEL_ID = "10000000-0000-0000-0000-000000000002"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str = "bob@sentinel.dev") -> str:
    response = client.post("/auth/login", json={"email": email, "password": "DemoPass123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_correlation_id_is_generated_when_absent_and_returned_in_the_header(client: TestClient):
    response = client.post("/auth/login", json={"email": "bob@sentinel.dev", "password": "DemoPass123!"})
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) > 10


def test_correlation_id_from_the_request_is_echoed_back_unchanged(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "bob@sentinel.dev", "password": "DemoPass123!"},
        headers={"X-Correlation-ID": "test-correlation-42"},
    )
    assert response.headers["X-Correlation-ID"] == "test-correlation-42"


def test_error_response_uses_the_uniform_envelope_and_includes_the_correlation_id(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "bob@sentinel.dev", "password": "wrong-password"},
        headers={"X-Correlation-ID": "test-correlation-err"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert "message" in body["error"]
    assert body["error"]["correlation_id"] == "test-correlation-err"
    assert response.headers["X-Correlation-ID"] == "test-correlation-err"


def test_message_access_denied_uses_the_documented_error_code(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")
    response = client.post(
        f"/channels/{PRIVATE_CHANNEL_ID}/messages",
        json={"content": "intento colarme"},
        headers=_auth(alice_token),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MESSAGE_ACCESS_DENIED"


def test_edit_message_endpoint_updates_content_and_broadcasts(client: TestClient):
    bob_token = _login(client)
    sent = client.post(f"/channels/{GENERAL_CHANNEL_ID}/messages", json={"content": "original"}, headers=_auth(bob_token)).json()

    with client.websocket_connect(f"/ws/channels/{GENERAL_CHANNEL_ID}?token={bob_token}") as ws:
        response = client.patch(f"/messages/{sent['id']}", json={"content": "editado"}, headers=_auth(bob_token))
        assert response.status_code == 200
        assert response.json()["content"] == "editado"
        assert response.json()["status"] == "edited"

        event = ws.receive_json()
        assert event["event"] == "message_edited"
        assert event["content"] == "editado"


def test_delete_message_endpoint_soft_deletes_and_broadcasts(client: TestClient):
    bob_token = _login(client)
    sent = client.post(f"/channels/{GENERAL_CHANNEL_ID}/messages", json={"content": "para borrar"}, headers=_auth(bob_token)).json()

    with client.websocket_connect(f"/ws/channels/{GENERAL_CHANNEL_ID}?token={bob_token}") as ws:
        response = client.delete(f"/messages/{sent['id']}", headers=_auth(bob_token))
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        assert response.json()["content"] is None

        event = ws.receive_json()
        assert event["event"] == "message_deleted"


def test_non_owner_cannot_edit_or_delete_someone_elses_message(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    alice_token = _login(client, "alice@sentinel.dev")
    sent = client.post(f"/channels/{GENERAL_CHANNEL_ID}/messages", json={"content": "de bob"}, headers=_auth(bob_token)).json()

    edit_response = client.patch(f"/messages/{sent['id']}", json={"content": "hackeado"}, headers=_auth(alice_token))
    assert edit_response.status_code == 403

    delete_response = client.delete(f"/messages/{sent['id']}", headers=_auth(alice_token))
    assert delete_response.status_code == 403
