from datetime import datetime
from typing import Optional

import psycopg

from backend.domain.entities import Message, SearchResult
from backend.domain.errors import MessageAccessDeniedError
from backend.domain.ports import MessageRepository

_RETURNING = "id, channel_id, sender_id, content, message_status, created_at, updated_at"


def _row_to_message(row) -> Message:
    id_, channel_id, sender_id, content, status, created_at, updated_at = row
    # el contenido de un mensaje eliminado nunca se expone, sin importar qué ruta SQL lo trajo
    # (RETURNING de un UPDATE, o get_channel_messages()) — la columna viva conserva el texto
    # real para que el trigger de auditoría pueda copiarlo a rw_message_history, pero de cara
    # a cualquier respuesta de la app un mensaje 'deleted' siempre reporta content=None (R06).
    if status == "deleted":
        content = None
    return Message(
        id=str(id_),
        channel_id=str(channel_id),
        sender_id=str(sender_id),
        content=content,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )


class PsycopgMessageRepository(MessageRepository):
    """Requiere que la conexión ya tenga el actor fijado (authorized_transaction) — todas
    las queries de acá son parametrizadas y dejan que RLS decida qué es visible/editable."""

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def create(self, channel_id: str, sender_id: str, content: str) -> Message:
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO rw_messages (channel_id, sender_id, content) VALUES (%s, %s, %s) RETURNING {_RETURNING}",
                    (channel_id, sender_id, content),
                )
                row = cur.fetchone()
        except psycopg.errors.InsufficientPrivilege as exc:
            raise MessageAccessDeniedError("Not authorized to post in this channel.") from exc
        return _row_to_message(row)

    def edit(self, message_id: str, new_content: str) -> Message:
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"UPDATE rw_messages SET content = %s WHERE id = %s RETURNING {_RETURNING}",
                    (new_content, message_id),
                )
                row = cur.fetchone()
        except psycopg.errors.InsufficientPrivilege as exc:
            raise MessageAccessDeniedError("Not authorized to edit this message.") from exc
        if row is None:
            raise MessageAccessDeniedError("Not authorized to edit this message.")
        return _row_to_message(row)

    def soft_delete(self, message_id: str) -> Message:
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"UPDATE rw_messages SET message_status = 'deleted' WHERE id = %s RETURNING {_RETURNING}",
                    (message_id,),
                )
                row = cur.fetchone()
        except psycopg.errors.InsufficientPrivilege as exc:
            raise MessageAccessDeniedError("Not authorized to delete this message.") from exc
        if row is None:
            raise MessageAccessDeniedError("Not authorized to delete this message.")
        return _row_to_message(row)

    def list_by_channel(
        self, channel_id: str, cursor_created_at: Optional[datetime], cursor_id: Optional[str], limit: int
    ) -> list[Message]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_channel_messages(%s, %s, %s, %s)",
                (channel_id, cursor_created_at, cursor_id, limit),
            )
            return [_row_to_message(row) for row in cur.fetchall()]

    def search(
        self, query: str, cursor_created_at: Optional[datetime], cursor_id: Optional[str], limit: int
    ) -> list[SearchResult]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM search_messages(%s, %s, %s, %s)",
                (query, cursor_created_at, cursor_id, limit),
            )
            rows = cur.fetchall()
        return [
            SearchResult(
                id=str(id_), channel_id=str(channel_id), sender_id=str(sender_id), headline=headline, created_at=created_at, rank=rank
            )
            for id_, channel_id, sender_id, headline, created_at, rank in rows
        ]
