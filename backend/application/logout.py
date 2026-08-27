from backend.application.tokens import hash_refresh_token
from backend.domain.ports import RefreshTokenRepository


class LogoutUseCase:
    """Idempotente y silenciosa a propósito: revocar un token ya revocado, o uno que no
    existe, no debe informarle al caller cuál de los dos casos fue (no leak de validez)."""

    def __init__(self, refresh_token_repository: RefreshTokenRepository):
        self._refresh_tokens = refresh_token_repository

    def execute(self, raw_refresh_token: str) -> None:
        record = self._refresh_tokens.find_by_hash(hash_refresh_token(raw_refresh_token))
        if record is not None and record.revoked_at is None:
            self._refresh_tokens.revoke(record.id, replaced_by_token_id=None)
