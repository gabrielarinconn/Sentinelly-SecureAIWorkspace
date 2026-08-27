from abc import ABC, abstractmethod
from typing import Optional

from backend.domain.entities import Message, User


class UserRepository(ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[tuple[User, str]]:
        """Returns (user, password_hash) for an active user, or None if not found."""


class MessageRepository(ABC):
    """Nunca agrega su propio filtro de autorización en SQL — RLS decide qué filas son
    visibles/editables (principio central del proyecto); esta interfaz solo ejecuta."""

    @abstractmethod
    def create(self, channel_id: str, sender_id: str, content: str) -> Message: ...

    @abstractmethod
    def edit(self, message_id: str, new_content: str) -> Message: ...

    @abstractmethod
    def soft_delete(self, message_id: str) -> Message: ...


class PasswordHasher(ABC):
    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, user_id: str) -> str: ...

    @abstractmethod
    def decode_access_token(self, token: str) -> str:
        """Returns the user_id (sub claim). Raises InvalidTokenError otherwise."""
