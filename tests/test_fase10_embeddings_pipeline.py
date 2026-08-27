"""Fase 10 DoD: insertar un mensaje deja una fila 'pending' en rw_message_embeddings sin
bloquear el INSERT; el worker la actualiza a 'completed' en segundo plano.
"""

from backend.application.login import LoginUseCase
from backend.application.send_message import SendMessageUseCase
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.embedding_provider import EMBEDDING_DIMENSIONS, LocalHashEmbeddingProvider
from backend.infrastructure.embedding_worker import process_pending_embeddings
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.message_repository import PsycopgMessageRepository
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.user_repository import PsycopgUserRepository

DEMO_PASSWORD = "DemoPass123!"
GENERAL_CHANNEL_ID = "10000000-0000-0000-0000-000000000001"


def _user_id_for(email: str) -> str:
    conn = get_app_connection()
    try:
        use_case = LoginUseCase(
            user_repository=PsycopgUserRepository(conn),
            password_hasher=BcryptPasswordHasher(),
            token_service=JwtTokenService(),
        )
        token = use_case.execute(email, DEMO_PASSWORD).access_token
        return JwtTokenService().decode_access_token(token)
    finally:
        conn.close()


def _embedding_row(message_id: str) -> tuple:
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status, embedding FROM rw_message_embeddings WHERE message_id = %s", (message_id,))
            return cur.fetchone()
    finally:
        conn.close()


def test_sending_a_message_immediately_creates_a_pending_embedding_row():
    bob_id = _user_id_for("bob@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            message = PsycopgMessageRepository(conn).create(GENERAL_CHANNEL_ID, bob_id, "mensaje para embeddings")
    finally:
        conn.close()

    status, embedding = _embedding_row(message.id)
    assert status == "pending"
    assert embedding is None  # el INSERT no esperó a ningún proveedor externo


def test_worker_processes_pending_rows_into_completed_with_a_real_dimension_vector():
    bob_id = _user_id_for("bob@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            message = PsycopgMessageRepository(conn).create(GENERAL_CHANNEL_ID, bob_id, "otro mensaje para el worker")
    finally:
        conn.close()

    processed = process_pending_embeddings(LocalHashEmbeddingProvider(), limit=10)
    assert processed >= 1

    status, embedding = _embedding_row(message.id)
    assert status == "completed"
    assert embedding is not None
    assert len(embedding) == EMBEDDING_DIMENSIONS


def test_editing_a_message_re_queues_its_embedding_as_pending():
    bob_id = _user_id_for("bob@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            repo = PsycopgMessageRepository(conn)
            message = repo.create(GENERAL_CHANNEL_ID, bob_id, "contenido original")
    finally:
        conn.close()

    process_pending_embeddings(LocalHashEmbeddingProvider(), limit=10)
    assert _embedding_row(message.id)[0] == "completed"

    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            PsycopgMessageRepository(conn).edit(message.id, "contenido editado")
    finally:
        conn.close()

    assert _embedding_row(message.id)[0] == "pending"


def test_deleting_a_message_does_not_re_queue_its_embedding():
    bob_id = _user_id_for("bob@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            repo = PsycopgMessageRepository(conn)
            message = repo.create(GENERAL_CHANNEL_ID, bob_id, "para borrar")
    finally:
        conn.close()

    process_pending_embeddings(LocalHashEmbeddingProvider(), limit=10)
    assert _embedding_row(message.id)[0] == "completed"

    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            PsycopgMessageRepository(conn).soft_delete(message.id)
    finally:
        conn.close()

    assert _embedding_row(message.id)[0] == "completed"  # no cambia: content no se tocó
