"""Fase 5 DoD: RLS sobre rw_channel_members — member ve la membresía de sus propios canales,
non-member no ve nada de un canal ajeno. Corre contra PostgreSQL real.
"""

from backend.application.login import LoginUseCase
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.user_repository import PsycopgUserRepository

DEMO_PASSWORD = "DemoPass123!"
PRIVATE_CHANNEL_ID = "10000000-0000-0000-0000-000000000002"


def _login(email: str) -> str:
    conn = get_app_connection()
    try:
        use_case = LoginUseCase(
            user_repository=PsycopgUserRepository(conn),
            password_hasher=BcryptPasswordHasher(),
            token_service=JwtTokenService(),
        )
        return use_case.execute(email, DEMO_PASSWORD).access_token
    finally:
        conn.close()


def _member_rows_visible_to(token: str) -> list[tuple]:
    user_id = JwtTokenService().decode_access_token(token)
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            with conn.cursor() as cur:
                cur.execute("SELECT channel_id, user_id, role FROM rw_channel_members ORDER BY channel_id, role;")
                return cur.fetchall()
    finally:
        conn.close()


def test_owner_sees_membership_of_the_private_channel_they_belong_to():
    bob_token = _login("bob@sentinel.dev")
    rows = _member_rows_visible_to(bob_token)
    channel_ids = {str(row[0]) for row in rows}
    assert PRIVATE_CHANNEL_ID in channel_ids


def test_non_member_never_sees_membership_of_a_private_channel_they_are_not_in():
    alice_token = _login("alice@sentinel.dev")
    rows = _member_rows_visible_to(alice_token)
    channel_ids = {str(row[0]) for row in rows}
    assert PRIVATE_CHANNEL_ID not in channel_ids


def test_member_write_is_denied_without_a_policy():
    """Sin policy de INSERT (D011, sin caso de uso real todavía), incluso el actor correcto
    no puede escribir — RLS deniega por defecto."""
    bob_token = _login("bob@sentinel.dev")
    user_id = JwtTokenService().decode_access_token(bob_token)
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            with conn.cursor() as cur:
                import psycopg

                try:
                    cur.execute(
                        "INSERT INTO rw_channel_members (channel_id, user_id, role) VALUES (%s, %s, 'member')",
                        (PRIVATE_CHANNEL_ID, "00000000-0000-0000-0000-000000000001"),
                    )
                    assert False, "expected RLS to deny this INSERT"
                except psycopg.errors.InsufficientPrivilege:
                    pass
    finally:
        conn.rollback()
        conn.close()
