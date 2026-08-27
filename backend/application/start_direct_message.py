from backend.domain.entities import Conversation
from backend.domain.ports import ConversationRepository


class StartDirectMessageUseCase:
    """Delgado: rw_get_or_create_dm_channel (SECURITY DEFINER) hace toda la validación real
    (no consigo mismo, usuario destino activo) — ver database/functions/0006."""

    def __init__(self, conversation_repository: ConversationRepository):
        self._conversations = conversation_repository

    def execute(self, other_user_id: str) -> Conversation:
        return self._conversations.get_or_create_dm(other_user_id)
