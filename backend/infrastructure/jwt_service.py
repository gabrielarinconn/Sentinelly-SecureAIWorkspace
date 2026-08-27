import os
import time
import uuid
from typing import Optional

import jwt

from backend.domain.errors import InvalidTokenError
from backend.domain.ports import TokenService


class JwtTokenService(TokenService):
    """JWT mínimo (Fase 4): solo `sub` + claims estándar. Sin name/role_title todavía — el
    origen exacto de nombre/cargo para el copiloto se decide en la Fase 18 (D012), no aquí."""

    def __init__(self, secret: Optional[str] = None, expires_minutes: Optional[int] = None):
        self._secret = secret or os.environ["JWT_SECRET"]
        self._expires_minutes = expires_minutes or int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "15"))

    def create_access_token(self, user_id: str) -> str:
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + self._expires_minutes * 60,
            "jti": str(uuid.uuid4()),
            "type": "access",
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def decode_access_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        if payload.get("type") != "access":
            raise InvalidTokenError("Not an access token.")
        return payload["sub"]
