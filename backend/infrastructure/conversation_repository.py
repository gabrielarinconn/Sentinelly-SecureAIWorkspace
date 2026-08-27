import psycopg

from backend.domain.entities import Conversation
from backend.domain.errors import ChannelAccessDeniedError, InvalidDirectMessageTargetError
from backend.domain.ports import ConversationRepository


class PsycopgConversationRepository(ConversationRepository):
    """Requiere una conexión dentro de authorized_transaction — view_user_conversations
    filtra por current_setting('app.current_user_id') internamente (Fase 9)."""

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def list_for_actor(self) -> list[Conversation]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT channel_id, channel_name, is_private, my_role, last_message_at, member_count, "
                "unread_count, is_direct, dm_peer_id, dm_peer_name "
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
                member_count=member_count,
                unread_count=unread_count,
                is_direct=is_direct,
                dm_peer_id=str(dm_peer_id) if dm_peer_id else None,
                dm_peer_name=dm_peer_name,
            )
            for (
                channel_id,
                channel_name,
                is_private,
                my_role,
                last_message_at,
                member_count,
                unread_count,
                is_direct,
                dm_peer_id,
                dm_peer_name,
            ) in rows
        ]

    def get_or_create_dm(self, other_user_id: str) -> Conversation:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT rw_get_or_create_dm_channel(%s)", (other_user_id,))
                (channel_id,) = cur.fetchone()
        except psycopg.errors.RaiseException as exc:
            raise InvalidDirectMessageTargetError(str(exc)) from exc
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT channel_id, channel_name, is_private, my_role, last_message_at, member_count, "
                "unread_count, is_direct, dm_peer_id, dm_peer_name "
                "FROM view_user_conversations WHERE channel_id = %s",
                (channel_id,),
            )
            row = cur.fetchone()
        (
            channel_id,
            channel_name,
            is_private,
            my_role,
            last_message_at,
            member_count,
            unread_count,
            is_direct,
            dm_peer_id,
            dm_peer_name,
        ) = row
        return Conversation(
            channel_id=str(channel_id),
            channel_name=channel_name,
            is_private=is_private,
            my_role=my_role,
            last_message_at=last_message_at,
            member_count=member_count,
            unread_count=unread_count,
            is_direct=is_direct,
            dm_peer_id=str(dm_peer_id) if dm_peer_id else None,
            dm_peer_name=dm_peer_name,
        )

    def mark_channel_read(self, channel_id: str, user_id: str) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO rw_channel_reads (channel_id, user_id, last_read_at) VALUES (%s, %s, now()) "
                    "ON CONFLICT (channel_id, user_id) DO UPDATE SET last_read_at = now()",
                    (channel_id, user_id),
                )
        except psycopg.errors.InsufficientPrivilege as exc:
            raise ChannelAccessDeniedError("Not authorized to mark this channel as read.") from exc
