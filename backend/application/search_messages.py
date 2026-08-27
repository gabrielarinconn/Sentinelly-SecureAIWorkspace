from backend.application.cursor import decode_cursor
from backend.domain.entities import SearchResult
from backend.domain.errors import EmptySearchQueryError
from backend.domain.ports import MessageRepository


class SearchMessagesUseCase:
    def __init__(self, message_repository: MessageRepository):
        self._messages = message_repository

    def execute(self, query: str, cursor: str | None = None, limit: int = 20) -> list[SearchResult]:
        if not query or not query.strip():
            raise EmptySearchQueryError("Search query cannot be blank.")
        cursor_created_at, cursor_id = decode_cursor(cursor)
        return self._messages.search(query, cursor_created_at, cursor_id, limit)
