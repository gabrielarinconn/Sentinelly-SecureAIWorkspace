from datetime import datetime, timedelta, timezone

from backend.application.tokens import generate_refresh_token, hash_refresh_token
from backend.domain.ports import RefreshTokenRepository


class IssueRefreshTokenUseCase:
    """Separado de LoginUseCase a propósito: LoginUseCase solo verifica credenciales y emite
    el access token (single responsibility) — esto se llama aparte, desde el endpoint de
    login, para no acoplar "verificar quién eres" con "abrir una sesión de largo plazo"."""

    def __init__(self, refresh_token_repository: RefreshTokenRepository, ttl_days: int = 7):
        self._refresh_tokens = refresh_token_repository
        self._ttl = timedelta(days=ttl_days)

    def execute(self, user_id: str) -> str:
        raw_token = generate_refresh_token()
        expires_at = datetime.now(timezone.utc) + self._ttl
        self._refresh_tokens.create(user_id, hash_refresh_token(raw_token), expires_at)
        return raw_token
