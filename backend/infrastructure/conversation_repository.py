import psycopg

from backend.domain.entities import Conversation
from backend.domain.ports import ConversationRepository


class PsycopgConversationRepository(ConversationRepository):
    """Requiere una conexión dentro de authorized_transaction — view_user_conversations
    filtra por current_setting('app.current_user_id') internamente (Fase 9)."""

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def list_for_actor(self) -> list[Conversation]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT channel_id, channel_name, is_private, my_role, last_message_at "
                "FROM view_user_conversations ORDER BY last_message_at DESC NULLS LAST"
            )
            rows = cur.fetchall()
        return [
            Conversation(
                channel_id=str(channel_id),
                channel_name=channel_name,
                is_private=is_private,
                my_role=my_role,
                last_message_at=last_message_at,
            )
            for channel_id, channel_name, is_private, my_role, last_message_at in rows
        ]
