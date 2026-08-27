from backend.domain.entities import Conversation
from backend.domain.ports import ConversationRepository


class ListChannelsUseCase:
    def __init__(self, conversation_repository: ConversationRepository):
        self._conversations = conversation_repository

    def execute(self) -> list[Conversation]:
        return self._conversations.list_for_actor()
