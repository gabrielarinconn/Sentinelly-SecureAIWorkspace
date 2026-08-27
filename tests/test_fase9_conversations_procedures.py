"""Fase 9 DoD: view_user_conversations retorna solo canales donde el actor es miembro
(verificado con 2 usuarios del seed); ambos procedimientos ejecutan sin bypass de RLS.
"""

from backend.application.login import LoginUseCase
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.user_repository import PsycopgUserRepository

DEMO_PASSWORD = "DemoPass123!"
ALICE_ID = "00000000-0000-0000-0000-000000000001"
BOB_ID = "00000000-0000-0000-0000-000000000002"


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


def _conversations_for(user_id: str) -> list[tuple]:
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            with conn.cursor() as cur:
                cur.execute("SELECT channel_name, is_private, my_role FROM view_user_conversations ORDER BY channel_name;")
                return cur.fetchall()
    finally:
        conn.close()


def test_view_shows_only_the_member_channel_for_alice():
    alice_id = _user_id_for("alice@sentinel.dev")
    rows = _conversations_for(alice_id)
    assert rows == [("general", False, "owner")]  # Alice creó 'general' en el seed


def test_view_shows_both_channels_for_bob_with_correct_roles():
    bob_id = _user_id_for("bob@sentinel.dev")
    rows = _conversations_for(bob_id)
    assert rows == [
        ("general", False, "member"),
        ("leadership-private", True, "owner"),
    ]


def test_query_users_procedure_finds_users_by_partial_name():
    alice_id = _user_id_for("alice@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, alice_id):
            with conn.cursor() as cur:
                cur.execute("CALL rw_query_users(%s)", ("bob",))
                cursor_name = cur.fetchone()[0]
                cur.execute(f'FETCH ALL FROM "{cursor_name}"')
                rows = cur.fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0][2] == "Bob Chen"  # full_name


def test_edit_user_procedure_only_ever_touches_the_calling_actor():
    alice_id = _user_id_for("alice@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, alice_id):
            with conn.cursor() as cur:
                cur.execute("CALL rw_edit_or_delete_user(%s, %s, %s)", ("Alice Updated", None, False))
                cur.execute("SELECT full_name FROM rw_users WHERE id = %s", (alice_id,))
                alice_name = cur.fetchone()[0]
                cur.execute("SELECT full_name FROM rw_users WHERE id = %s", (BOB_ID,))
                bob_name = cur.fetchone()[0]
    finally:
        conn.close()
    assert alice_name == "Alice Updated"
    assert bob_name == "Bob Chen"  # nunca se tocó — no hay forma de pasar otro user_id


def test_deactivate_procedure_is_soft_delete_not_a_physical_delete():
    alice_id = _user_id_for("alice@sentinel.dev")
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, alice_id):
            with conn.cursor() as cur:
                cur.execute("CALL rw_edit_or_delete_user(%s, %s, %s)", (None, None, True))
                cur.execute("SELECT is_active FROM rw_users WHERE id = %s", (alice_id,))
                is_active = cur.fetchone()[0]
    finally:
        conn.close()
    assert is_active is False
