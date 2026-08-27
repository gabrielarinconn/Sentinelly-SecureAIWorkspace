"""Fase 20: inyección SQL. Todas las queries del proyecto son parametrizadas (regla dura) —
estos tests demuestran que un payload de inyección se trata como dato literal, nunca como SQL
ejecutable, en cada punto de entrada de texto libre del usuario.
"""

import pytest
from fastapi.testclient import TestClient

from backend.presentation.api import app

GENERAL_CHANNEL_ID = "10000000-0000-0000-0000-000000000001"

INJECTION_PAYLOADS = [
    "'; DROP TABLE rw_messages; --",
    "' OR '1'='1",
    "'; DELETE FROM rw_users; --",
    "budget' UNION SELECT password_hash, NULL, NULL, NULL, NULL, NULL FROM rw_users --",
]


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


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_login_email_field_never_executes_injected_sql(client: TestClient, payload: str):
    response = client.post("/auth/login", json={"email": payload, "password": "whatever"})
    assert response.status_code == 401  # se trata como email inexistente, no como SQL

    # rw_users sigue intacto: el login legítimo de después sigue funcionando.
    ok = client.post("/auth/login", json={"email": "bob@sentinel.dev", "password": "DemoPass123!"})
    assert ok.status_code == 200


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_search_query_never_executes_injected_sql(client: TestClient, payload: str):
    bob_token = _login(client)
    response = client.get("/messages/search", params={"q": payload}, headers=_auth(bob_token))
    assert response.status_code == 200  # se trata como texto de búsqueda literal, no rompe la query

    # rw_messages sigue intacto: la búsqueda legítima de después sigue devolviendo resultados.
    ok = client.get("/messages/search", params={"q": "budget"}, headers=_auth(bob_token))
    assert ok.status_code == 200
    assert len(ok.json()["items"]) > 0


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_message_content_never_executes_injected_sql(client: TestClient, payload: str):
    bob_token = _login(client)
    response = client.post(f"/channels/{GENERAL_CHANNEL_ID}/messages", json={"content": payload}, headers=_auth(bob_token))
    assert response.status_code == 200
    assert response.json()["content"] == payload  # se guardó tal cual, como texto — no se ejecutó

    still_there = client.get(f"/channels/{GENERAL_CHANNEL_ID}/messages", headers=_auth(bob_token))
    assert still_there.status_code == 200
    assert len(still_there.json()["items"]) > 0  # rw_messages sigue intacto
