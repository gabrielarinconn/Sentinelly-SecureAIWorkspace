from backend.domain.entities import Message
from backend.domain.errors import EmptyMessageError
from backend.domain.ports import MessageRepository


class SendMessageUseCase:
    """Delgado: Validate → Call DB function → Map result. La autorización real (¿puede este
    usuario postear en este canal?) la decide RLS, no esta clase."""

    def __init__(self, message_repository: MessageRepository):
        self._messages = message_repository

    def execute(self, channel_id: str, sender_id: str, content: str) -> Message:
        if not content or not content.strip():
            raise EmptyMessageError("Message content cannot be blank.")
        return self._messages.create(channel_id=channel_id, sender_id=sender_id, content=content)
