from dataclasses import dataclass

from backend.domain.errors import InvalidCredentialsError
from backend.domain.ports import PasswordHasher, TokenService, UserRepository


@dataclass
class LoginResult:
    access_token: str
    token_type: str = "bearer"


class LoginUseCase:
    """Validate → look up → verify → issue token. No FastAPI, no driver, no JWT SDK here —
    only domain ports (Strategy pattern, D010)."""

    def __init__(self, user_repository: UserRepository, password_hasher: PasswordHasher, token_service: TokenService):
        self._users = user_repository
        self._hasher = password_hasher
        self._tokens = token_service

    def execute(self, email: str, password: str) -> LoginResult:
        found = self._users.find_by_email(email)
        if found is None:
            raise InvalidCredentialsError("Invalid email or password.")
        user, password_hash = found
        if not self._hasher.verify(password, password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        token = self._tokens.create_access_token(user.id)
        return LoginResult(access_token=token)
