from backend.domain.entities import Message
from backend.domain.ports import MessageRepository


class DeleteMessageUseCase:
    def __init__(self, message_repository: MessageRepository):
        self._messages = message_repository

    def execute(self, message_id: str) -> Message:
        return self._messages.soft_delete(message_id=message_id)
