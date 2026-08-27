from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from backend.domain.entities import (
    Conversation,
    CopilotUsage,
    LLMCompletion,
    Message,
    RefreshTokenRecord,
    RetrievedContext,
    SearchResult,
    User,
)


class UserRepository(ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[tuple[User, str]]:
        """Returns (user, password_hash) for an active user, or None if not found."""

    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional[User]: ...


class ConversationRepository(ABC):
    @abstractmethod
    def list_for_actor(self) -> list[Conversation]:
        """view_user_conversations ya filtra por app.current_user_id (security_invoker) —
        no recibe un user_id como parámetro, el actor viene de la transacción."""


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

    @abstractmethod
    def retrieve_context(self, query_embedding: list[float], limit: int) -> list[RetrievedContext]:
        """retrieve_ai_context() (Fase 12) — RLS-gated, jamás "todos los mensajes filtrados
        después" (principio central del proyecto)."""


class RefreshTokenRepository(ABC):
    """Fase 15 — rotación + reuse detection. Solo trata con el hash del token, nunca con el
    valor crudo (regla dura: ningún secreto en texto plano)."""

    @abstractmethod
    def create(self, user_id: str, token_hash: str, expires_at: datetime) -> str:
        """Devuelve el id del nuevo token."""

    @abstractmethod
    def find_by_hash(self, token_hash: str) -> Optional[RefreshTokenRecord]: ...

    @abstractmethod
    def revoke(self, token_id: str, replaced_by_token_id: Optional[str]) -> None: ...

    @abstractmethod
    def revoke_all_active_for_user(self, user_id: str) -> None:
        """Respuesta a reuse detection: si un token ya revocado se vuelve a presentar, se
        asume la cadena de rotación comprometida y se revoca todo lo que siga activo."""


class CopilotUsageRepository(ABC):
    @abstractmethod
    def record(self, user_id: str, prompt_tokens: int, completion_tokens: int) -> None: ...

    @abstractmethod
    def get_for_actor(self) -> CopilotUsage:
        """get_user_copilot_usage() — igual que list_for_actor(), sin parámetro de user_id;
        el actor viene de la transacción, no de un argumento manipulable."""


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
    def complete(self, system_prompt: str, user_prompt: str) -> LLMCompletion: ...
