from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from backend.application.tokens import generate_refresh_token, hash_refresh_token
from backend.domain.errors import InvalidRefreshTokenError
from backend.domain.ports import RefreshTokenRepository, TokenService


@dataclass
class RefreshResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenUseCase:
    """Rotación (Fase 15): Refresh A -> Revoke A -> Create B, encadenados por
    replaced_by_token_id. Reuse detection: si A ya estaba revocado y alguien lo presenta de
    nuevo, se asume robo y se revoca toda la cadena activa del usuario — DENY explícito."""

    def __init__(self, refresh_token_repository: RefreshTokenRepository, token_service: TokenService, ttl_days: int = 7):
        self._refresh_tokens = refresh_token_repository
        self._tokens = token_service
        self._ttl = timedelta(days=ttl_days)

    def execute(self, raw_refresh_token: str) -> RefreshResult:
        token_hash = hash_refresh_token(raw_refresh_token)
        record = self._refresh_tokens.find_by_hash(token_hash)
        if record is None:
            raise InvalidRefreshTokenError("Refresh token not recognized.")

        if record.revoked_at is not None:
            self._refresh_tokens.revoke_all_active_for_user(record.user_id)
            raise InvalidRefreshTokenError("Refresh token reuse detected.")

        if record.expires_at <= datetime.now(timezone.utc):
            raise InvalidRefreshTokenError("Refresh token expired.")

        new_raw_token = generate_refresh_token()
        new_expires_at = datetime.now(timezone.utc) + self._ttl
        new_token_id = self._refresh_tokens.create(record.user_id, hash_refresh_token(new_raw_token), new_expires_at)
        self._refresh_tokens.revoke(record.id, replaced_by_token_id=new_token_id)

        access_token = self._tokens.create_access_token(record.user_id)
        return RefreshResult(access_token=access_token, refresh_token=new_raw_token)
