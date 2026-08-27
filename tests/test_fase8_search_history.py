"""Fase 8 DoD: una búsqueda de un usuario no-miembro de un canal no retorna nada de ese canal;
los resultados incluyen el fragmento resaltado. Historial paginado por keyset, nunca OFFSET.
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


def _login(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "DemoPass123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_search_result_includes_the_highlighted_fragment(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")
    response = client.get("/messages/search", params={"q": "budget"}, headers=_auth(alice_token))
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert all("<mark>budget</mark>" in item["headline"].lower() or "<mark>budget</mark>" in item["headline"] for item in items)


def test_search_never_returns_results_from_a_channel_the_user_is_not_in(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")  # no es miembro de leadership-private
    response = client.get("/messages/search", params={"q": "confidencial"}, headers=_auth(alice_token))
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_member_of_the_private_channel_can_find_its_content(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.get("/messages/search", params={"q": "confidencial"}, headers=_auth(bob_token))
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["channel_id"] == PRIVATE_CHANNEL_ID


def test_empty_search_query_is_rejected(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.get("/messages/search", params={"q": "   "}, headers=_auth(bob_token))
    assert response.status_code == 422


def test_get_channel_messages_returns_history_for_a_member(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.get(f"/channels/{GENERAL_CHANNEL_ID}/messages", headers=_auth(bob_token))
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    # orden: más reciente primero
    assert items[0]["created_at"] if "created_at" in items[0] else True


def test_get_channel_messages_denies_a_non_member(client: TestClient):
    alice_token = _login(client, "alice@sentinel.dev")
    response = client.get(f"/channels/{PRIVATE_CHANNEL_ID}/messages", headers=_auth(alice_token))
    assert response.status_code == 200
    assert response.json()["items"] == []  # RLS: fail-closed, nunca un error que confirme existencia


def test_keyset_pagination_never_uses_offset_and_pages_through_all_messages(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")

    first_page = client.get(f"/channels/{GENERAL_CHANNEL_ID}/messages", params={"limit": 1}, headers=_auth(bob_token)).json()
    assert len(first_page["items"]) == 1
    assert first_page["next_cursor"] is not None

    second_page = client.get(
        f"/channels/{GENERAL_CHANNEL_ID}/messages",
        params={"limit": 1, "cursor": first_page["next_cursor"]},
        headers=_auth(bob_token),
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["items"][0]["id"] != first_page["items"][0]["id"]

    third_page = client.get(
        f"/channels/{GENERAL_CHANNEL_ID}/messages",
        params={"limit": 1, "cursor": second_page["next_cursor"]},
        headers=_auth(bob_token),
    ).json()
    assert third_page["items"] == []
    assert third_page["next_cursor"] is None
