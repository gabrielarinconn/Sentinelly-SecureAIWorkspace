from typing import Optional

import psycopg

from backend.domain.entities import User
from backend.domain.ports import UserRepository


class PsycopgUserRepository(UserRepository):
    """rw_users no tiene RLS en esta fase (Fase 4 cubre solo rw_channels/rw_messages) — el
    login necesita poder buscar por email antes de que exista un actor autenticado."""

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def find_by_email(self, email: str) -> Optional[tuple[User, str]]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, full_name, role_title, is_active, password_hash
                FROM rw_users
                WHERE lower(email) = lower(%s) AND is_active = true
                """,
                (email,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        user_id, user_email, full_name, role_title, is_active, password_hash = row
        user = User(id=str(user_id), email=user_email, full_name=full_name, role_title=role_title, is_active=is_active)
        return user, password_hash

    def find_by_id(self, user_id: str) -> Optional[User]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, full_name, role_title, is_active FROM rw_users WHERE id = %s AND is_active = true",
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        id_, email, full_name, role_title, is_active = row
        return User(id=str(id_), email=email, full_name=full_name, role_title=role_title, is_active=is_active)
