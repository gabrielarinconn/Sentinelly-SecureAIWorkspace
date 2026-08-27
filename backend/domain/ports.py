from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from backend.domain.entities import Message, SearchResult, User


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

    @abstractmethod
    def list_by_channel(
        self, channel_id: str, cursor_created_at: Optional[datetime], cursor_id: Optional[str], limit: int
    ) -> list[Message]:
        """Historial paginado por keyset (D005) — get_channel_messages()."""

    @abstractmethod
    def search(
        self, query: str, cursor_created_at: Optional[datetime], cursor_id: Optional[str], limit: int
    ) -> list[SearchResult]:
        """Búsqueda con highlighting, keyset pagination — search_messages()."""


class PasswordHasher(ABC):
    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, user_id: str) -> str: ...

    @abstractmethod
    def decode_access_token(self, token: str) -> str:
        """Returns the user_id (sub claim). Raises InvalidTokenError otherwise."""


class EmbeddingProvider(ABC):
    """Interfaz mínima (D007) — un solo proveedor real detrás, intercambiable sin tocar el
    resto de la app. El resto del sistema nunca importa el SDK concreto directamente."""

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...


class LLMProvider(ABC):
    """Interfaz mínima (D007) para el copiloto — implementada en la Fase 18."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...
