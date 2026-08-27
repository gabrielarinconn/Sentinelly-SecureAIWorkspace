from datetime import datetime
from typing import Optional

import psycopg

from backend.domain.entities import RefreshTokenRecord
from backend.domain.ports import RefreshTokenRepository


class PsycopgRefreshTokenRepository(RefreshTokenRepository):
    """rw_refresh_tokens no tiene RLS — el flujo de login/refresh ocurre ANTES de que exista
    un actor derivado de un JWT ya verificado (la identidad se deriva del propio token que se
    está validando), así que no hay app.current_user_id que fijar todavía."""

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def create(self, user_id: str, token_hash: str, expires_at: datetime) -> str:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO rw_refresh_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s) RETURNING id",
                (user_id, token_hash, expires_at),
            )
            token_id = cur.fetchone()[0]
        return str(token_id)

    def find_by_hash(self, token_hash: str) -> Optional[RefreshTokenRecord]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, revoked_at, replaced_by_token_id, expires_at FROM rw_refresh_tokens WHERE token_hash = %s",
                (token_hash,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        id_, user_id, revoked_at, replaced_by_token_id, expires_at = row
        return RefreshTokenRecord(
            id=str(id_),
            user_id=str(user_id),
            revoked_at=revoked_at,
            replaced_by_token_id=str(replaced_by_token_id) if replaced_by_token_id else None,
            expires_at=expires_at,
        )

    def revoke(self, token_id: str, replaced_by_token_id: Optional[str]) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE rw_refresh_tokens SET revoked_at = now(), replaced_by_token_id = %s WHERE id = %s AND revoked_at IS NULL",
                (replaced_by_token_id, token_id),
            )

    def revoke_all_active_for_user(self, user_id: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE rw_refresh_tokens SET revoked_at = now() WHERE user_id = %s AND revoked_at IS NULL",
                (user_id,),
            )
