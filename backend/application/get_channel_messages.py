from backend.application.cursor import decode_cursor
from backend.domain.entities import Message
from backend.domain.ports import MessageRepository


class GetChannelMessagesUseCase:
    def __init__(self, message_repository: MessageRepository):
        self._messages = message_repository

    def execute(self, channel_id: str, cursor: str | None = None, limit: int = 50) -> list[Message]:
        cursor_created_at, cursor_id = decode_cursor(cursor)
        return self._messages.list_by_channel(channel_id, cursor_created_at, cursor_id, limit)
