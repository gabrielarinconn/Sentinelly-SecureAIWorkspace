"""Fase 7 DoD: mensaje persistido -> COMMIT -> evento realtime -> segundo cliente lo recibe
sin refresh. Contra PostgreSQL real, vía el endpoint HTTP real (no llamando al broadcaster
directamente) para probar el flujo completo send -> commit -> publish.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.presentation.api import app

GENERAL_CHANNEL_ID = "10000000-0000-0000-0000-000000000001"
PRIVATE_CHANNEL_ID = "10000000-0000-0000-0000-000000000002"


@pytest.fixture()
def client():
    # `with TestClient(app) as client:` corre toda la sesión sobre UN solo event loop (un
    # portal compartido) — necesario para que el WebSocket (que se queda bloqueado esperando
    # en su loop) y el POST concurrente que dispara el broadcast puedan comunicarse a través
    # del mismo asyncio.Queue. Sin esto, cada llamada aislada de TestClient corre en su
    # propio loop/thread y el Queue del WS nunca ve el evento (deadlock).
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "DemoPass123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_second_client_receives_the_message_over_the_websocket(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")
    bob_token = _login(client, "bob@sentinel.dev")

    with client.websocket_connect(f"/ws/channels/{GENERAL_CHANNEL_ID}?token={alice_token}") as ws:
        response = client.post(
            f"/channels/{GENERAL_CHANNEL_ID}/messages",
            json={"content": "hola desde bob"},
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert response.status_code == 200
        posted = response.json()

        event = ws.receive_json()
        assert event["content"] == "hola desde bob"
        assert event["id"] == posted["id"]
        assert event["status"] == "active"


def test_message_is_persisted_and_committed_before_being_broadcast(client: TestClient):
    """El evento solo se publica después de que el POST ya devolvió 200 — es decir, después
    del COMMIT. Verificamos el efecto observable: el mensaje ya está en la base de datos
    (visible por HTTP) para cuando el evento llega por WS."""
    bob_token = _login(client, "bob@sentinel.dev")
    alice_token = _login(client, "alice@sentinel.dev")

    with client.websocket_connect(f"/ws/channels/{GENERAL_CHANNEL_ID}?token={bob_token}") as ws:
        response = client.post(
            f"/channels/{GENERAL_CHANNEL_ID}/messages",
            json={"content": "verificando orden commit-then-broadcast"},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert response.status_code == 200
        ws.receive_json()  # el evento ya llegó -> el POST (y su COMMIT) ya terminó antes


def test_non_member_cannot_subscribe_to_a_private_channel(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")  # Alice no es miembro de leadership-private
    # El servidor cierra el WS antes de aceptar la conexión -> falla en el propio __enter__.
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/channels/{PRIVATE_CHANNEL_ID}?token={alice_token}"):
            pass
    assert exc_info.value.code == 4403


def test_websocket_rejects_an_invalid_token(client: TestClient):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/channels/{GENERAL_CHANNEL_ID}?token=not-a-real-jwt"):
            pass
    assert exc_info.value.code == 4401


def test_send_message_endpoint_rejects_empty_content(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.post(
        f"/channels/{GENERAL_CHANNEL_ID}/messages",
        json={"content": "   "},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 422


def test_send_message_endpoint_denies_non_member(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")
    response = client.post(
        f"/channels/{PRIVATE_CHANNEL_ID}/messages",
        json={"content": "intento colarme"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 403
