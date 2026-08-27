from backend.domain.ports import ConversationRepository


class MarkChannelReadUseCase:
    """Delgado: RLS (rw_channel_reads_own_insert/update) decide si el actor puede marcar este
    canal como leído, no esta clase — igual criterio que SendMessageUseCase."""

    def __init__(self, conversation_repository: ConversationRepository):
        self._conversations = conversation_repository

    def execute(self, channel_id: str, user_id: str) -> None:
        self._conversations.mark_channel_read(channel_id=channel_id, user_id=user_id)
