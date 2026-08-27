from pathlib import Path

from backend.domain.entities import Citation, CopilotAnswer, RetrievedContext
from backend.domain.errors import EmptySearchQueryError
from backend.domain.ports import CopilotUsageRepository, EmbeddingProvider, LLMProvider, MessageRepository, UserRepository

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "copilot_v1.txt"


class AskCopilotUseCase:
    """Pipeline exigido por la Fase 12/18 (principio central del proyecto):

        pregunta -> embedding -> retrieve_ai_context() (RLS ya aplicado) -> prompt -> LLM

    El LLM nunca ve más que el `context_block` ya filtrado por RLS — ni siquiera sabe que
    existen canales fuera de ese contexto. "Authorization happens before generation": para
    cuando el LLM entra en escena, la autorización ya se decidió en SQL.
    """

    def __init__(
        self,
        message_repository: MessageRepository,
        user_repository: UserRepository,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        copilot_usage_repository: CopilotUsageRepository,
    ):
        self._messages = message_repository
        self._users = user_repository
        self._embeddings = embedding_provider
        self._llm = llm_provider
        self._usage = copilot_usage_repository

    def execute(self, user_id: str, question: str) -> CopilotAnswer:
        if not question or not question.strip():
            raise EmptySearchQueryError("Question cannot be blank.")

        user = self._users.find_by_id(user_id)
        if user is None:
            # el JWT ya fue verificado más arriba; si el usuario desapareció/se desactivó
            # entre el login y esta pregunta, no hay identidad de servidor que inyectar.
            raise EmptySearchQueryError("User not found.")

        query_embedding = self._embeddings.embed(question)
        context_items = self._messages.retrieve_context(query_embedding, limit=5)

        system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").format(
            user_full_name=user.full_name,
            user_role_title=user.role_title,
            context_block=_format_context(context_items),
        )
        completion = self._llm.complete(system_prompt, question)
        self._usage.record(user_id, completion.prompt_tokens, completion.completion_tokens)

        citations = [Citation(message_id=item.message_id, channel_id=item.channel_id) for item in context_items]
        return CopilotAnswer(answer=completion.text, citations=citations)


def _format_context(items: list[RetrievedContext]) -> str:
    if not items:
        return "(sin resultados autorizados para esta pregunta)"
    return "\n".join(f"[{i}] {item.content}" for i, item in enumerate(items, start=1))
