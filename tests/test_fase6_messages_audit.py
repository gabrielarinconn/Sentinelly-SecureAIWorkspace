"""Fase 6 DoD: editar/eliminar un mensaje deja rastro completo en rw_message_history, y un
DELETE físico está bloqueado. Todo contra PostgreSQL real, actor real vía JWT.
"""

import psycopg
import pytest

from backend.application.delete_message import DeleteMessageUseCase
from backend.application.edit_message import EditMessageUseCase
from backend.application.login import LoginUseCase
from backend.application.send_message import SendMessageUseCase
from backend.domain.errors import EmptyMessageError, MessageAccessDeniedError
from backend.infrastructure.db import authorized_transaction, get_app_connection
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


def _history_for(message_id: str, as_user_id: str) -> list[tuple]:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, as_user_id):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT previous_content, previous_status, action, changed_by "
                    "FROM rw_message_history WHERE message_id = %s ORDER BY changed_at",
                    (message_id,),
                )
                return [(content, status, action, str(changed_by)) for content, status, action, changed_by in cur.fetchall()]
    finally:
        conn.close()


def test_send_edit_delete_leaves_a_full_audit_trail():
    bob_id = _user_id_for("bob@sentinel.dev")

    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            repo = PsycopgMessageRepository(conn)
            message = SendMessageUseCase(repo).execute(GENERAL_CHANNEL_ID, bob_id, "mensaje original")
            assert message.status == "active"

            edited = EditMessageUseCase(repo).execute(message.id, "mensaje corregido")
            assert edited.status == "edited"
            assert edited.content == "mensaje corregido"

            deleted = DeleteMessageUseCase(repo).execute(message.id)
            assert deleted.status == "deleted"
    finally:
        conn.close()

    history = _history_for(message.id, bob_id)
    assert len(history) == 2
    assert history[0] == ("mensaje original", "active", "edit", bob_id)
    assert history[1] == ("mensaje corregido", "edited", "delete", bob_id)


def test_cannot_modify_an_already_deleted_message():
    bob_id = _user_id_for("bob@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            repo = PsycopgMessageRepository(conn)
            message = SendMessageUseCase(repo).execute(GENERAL_CHANNEL_ID, bob_id, "para borrar")
            DeleteMessageUseCase(repo).execute(message.id)
            with pytest.raises(psycopg.errors.RaiseException, match="already deleted"):
                repo.edit(message.id, "resucitado")
    finally:
        conn.rollback()
        conn.close()


def test_non_owner_cannot_edit_someone_elses_message():
    alice_id = _user_id_for("alice@sentinel.dev")
    bob_id = _user_id_for("bob@sentinel.dev")

    conn = get_app_connection()
    try:
        with authorized_transaction(conn, bob_id):
            message = PsycopgMessageRepository(conn).create(GENERAL_CHANNEL_ID, bob_id, "mensaje de bob")
    finally:
        conn.close()

    conn = get_app_connection()
    try:
        with authorized_transaction(conn, alice_id):
            repo = PsycopgMessageRepository(conn)
            with pytest.raises(MessageAccessDeniedError):
                EditMessageUseCase(repo).execute(message.id, "hackeado")
    finally:
        conn.close()


def test_cannot_send_impersonating_another_sender():
    alice_id = _user_id_for("alice@sentinel.dev")
    bob_id = _user_id_for("bob@sentinel.dev")

    conn = get_app_connection()
    try:
        with authorized_transaction(conn, alice_id):
            repo = PsycopgMessageRepository(conn)
            with pytest.raises(MessageAccessDeniedError):
                SendMessageUseCase(repo).execute(GENERAL_CHANNEL_ID, bob_id, "finjo ser bob")
    finally:
        conn.rollback()
        conn.close()


def test_empty_content_is_rejected_before_hitting_the_database():
    with pytest.raises(EmptyMessageError):
        SendMessageUseCase(message_repository=None).execute(GENERAL_CHANNEL_ID, "x", "   ")


def test_physical_delete_is_blocked_by_privileges_not_just_by_convention():
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute("DELETE FROM rw_messages WHERE content = 'anything'")
    finally:
        conn.rollback()
        conn.close()
