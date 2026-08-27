from backend.domain.entities import Message
from backend.domain.errors import EmptyMessageError
from backend.domain.ports import MessageRepository


class EditMessageUseCase:
    def __init__(self, message_repository: MessageRepository):
        self._messages = message_repository

    def execute(self, message_id: str, new_content: str) -> Message:
        if not new_content or not new_content.strip():
            raise EmptyMessageError("Message content cannot be blank.")
        return self._messages.edit(message_id=message_id, new_content=new_content)
