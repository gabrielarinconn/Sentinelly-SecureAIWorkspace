"""Fase 18 DoD: el copiloto responde "quién soy" con nombre/cargo correctos sin que el
usuario los haya mencionado; cita fuentes; consumo se registra por usuario. Llamadas reales a
DeepSeek y al modelo local de embeddings — nada de esto se mockea (misma filosofía que el
resto del proyecto: se prueba contra la infraestructura real).
"""

import pytest
from fastapi.testclient import TestClient

from backend.infrastructure.embedding_worker import process_pending_embeddings
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


@pytest.fixture()
def seed_embeddings_ready(real_embedding_provider):
    """Procesa los embeddings 'pending' del seed con el proveedor real antes de cada test que
    necesite retrieval funcionando."""
    process_pending_embeddings(real_embedding_provider, limit=50)


def test_copilot_knows_name_and_role_without_being_asked_directly(client: TestClient, seed_embeddings_ready):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.post("/copilot/ask", json={"question": "¿Quién soy? Dime mi nombre y mi cargo."}, headers=_auth(bob_token))
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert "bob" in answer
    assert "engineering" in answer or "lead" in answer


def test_copilot_answers_about_authorized_content_with_citations(client: TestClient, seed_embeddings_ready):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.post(
        "/copilot/ask", json={"question": "¿Qué se dijo sobre el budget del próximo trimestre?"}, headers=_auth(bob_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["answer"]) > 0
    assert len(body["citations"]) > 0
    # Bob SÍ es miembro de leadership-private (seed) — que aparezca citado no es una fuga,
    # es RLS permitiendo correctamente lo que le corresponde. La garantía de no-fuga para un
    # NO-miembro está en test_copilot_never_cites_a_channel_the_user_is_not_a_member_of.
    assert any(c["channel_id"] == GENERAL_CHANNEL_ID for c in body["citations"])


def test_copilot_never_cites_a_channel_the_user_is_not_a_member_of(client: TestClient, seed_embeddings_ready):
    alice_token = _login(client, "alice@sentinel.dev")  # no es miembro de leadership-private
    response = client.post(
        "/copilot/ask",
        json={"question": "Cuéntame todo lo que sepas sobre la discusión confidencial de liderazgo."},
        headers=_auth(alice_token),
    )
    assert response.status_code == 200
    citations = response.json()["citations"]
    assert all(c["channel_id"] != PRIVATE_CHANNEL_ID for c in citations)
    # garantía estructural: el contenido privado nunca estuvo en el contexto que vio el LLM,
    # así que no puede aparecer citado textualmente en la respuesta salvo alucinación exacta.
    assert "fuera del alcance de Alice" not in response.json()["answer"]


def test_copilot_rejects_an_empty_question(client: TestClient):
    bob_token = _login(client, "bob@sentinel.dev")
    response = client.post("/copilot/ask", json={"question": "   "}, headers=_auth(bob_token))
    assert response.status_code == 422


def test_copilot_usage_is_tracked_per_user_and_isolated(client: TestClient, seed_embeddings_ready):
    bob_token = _login(client, "bob@sentinel.dev")
    alice_token = _login(client, "alice@sentinel.dev")

    client.post("/copilot/ask", json={"question": "¿Quién soy?"}, headers=_auth(bob_token))
    client.post("/copilot/ask", json={"question": "¿Quién soy?"}, headers=_auth(bob_token))

    bob_usage = client.get("/copilot/usage", headers=_auth(bob_token)).json()
    alice_usage = client.get("/copilot/usage", headers=_auth(alice_token)).json()

    assert bob_usage["total_questions"] == 2
    assert bob_usage["total_prompt_tokens"] > 0
    assert bob_usage["total_completion_tokens"] > 0
    assert alice_usage["total_questions"] == 0  # las preguntas de Bob no se filtran a Alice
