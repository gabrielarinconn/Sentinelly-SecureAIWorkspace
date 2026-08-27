"""Fase 4 DoD: member puede leer, non-member no puede leer, el actor viene de un JWT real
(no simulado) vía app.current_user_id, y el rol de DB no tiene BYPASSRLS. Corre contra
PostgreSQL real (docker compose), nunca mocks.
"""

import pytest

from backend.application.login import LoginUseCase
from backend.domain.errors import InvalidCredentialsError
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.user_repository import PsycopgUserRepository

DEMO_PASSWORD = "DemoPass123!"


def _login(email: str, password: str = DEMO_PASSWORD) -> str:
    conn = get_app_connection()
    try:
        use_case = LoginUseCase(
            user_repository=PsycopgUserRepository(conn),
            password_hasher=BcryptPasswordHasher(),
            token_service=JwtTokenService(),
        )
        return use_case.execute(email, password).access_token
    finally:
        conn.close()


def _channel_names_visible_to(token: str) -> list[str]:
    user_id = JwtTokenService().decode_access_token(token)
    conn = get_app_connection()
    try:
        with authorized_transaction(conn, user_id):
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM rw_channels ORDER BY name;")
                return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def test_login_issues_a_real_signed_jwt():
    token = _login("alice@sentinel.dev")
    assert token.count(".") == 2  # header.payload.signature


def test_invalid_credentials_are_rejected():
    conn = get_app_connection()
    try:
        use_case = LoginUseCase(
            user_repository=PsycopgUserRepository(conn),
            password_hasher=BcryptPasswordHasher(),
            token_service=JwtTokenService(),
        )
        with pytest.raises(InvalidCredentialsError):
            use_case.execute("alice@sentinel.dev", "wrong-password")
    finally:
        conn.close()


def test_member_sees_only_the_channel_she_belongs_to():
    alice_token = _login("alice@sentinel.dev")
    assert _channel_names_visible_to(alice_token) == ["general"]


def test_member_of_both_channels_sees_both():
    bob_token = _login("bob@sentinel.dev")
    assert _channel_names_visible_to(bob_token) == ["general", "leadership-private"]


def test_non_member_never_sees_the_private_channel():
    alice_token = _login("alice@sentinel.dev")
    assert "leadership-private" not in _channel_names_visible_to(alice_token)


def test_actor_never_set_denies_by_default():
    """Fail-closed: sin SET LOCAL app.current_user_id, RLS no expone nada."""
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM rw_channels;")
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_app_role_has_no_superuser_or_bypassrls():
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;")
            rolsuper, rolbypassrls = cur.fetchone()
            assert rolsuper is False
            assert rolbypassrls is False
    finally:
        conn.close()
