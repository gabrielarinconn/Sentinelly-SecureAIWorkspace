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
        # Orden cronológico (no por similitud) antes de mostrárselo al LLM: retrieve_ai_context()
        # devuelve los más parecidos semánticamente, pero sin esto el modelo no tiene forma de
        # saber cuál mensaje es más nuevo si dos se contradicen (ej. un cambio de horario) — ver
        # regla 8 del prompt. Reordenar aquí también reordena las citas devueltas al frontend,
        # así el número [N] que cita el LLM sigue correspondiendo a la misma tarjeta de cita.
        context_items = sorted(context_items, key=lambda item: item.created_at)

        system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").format(
            user_full_name=user.full_name,
            user_role_title=user.role_title,
            context_block=_format_context(context_items),
        )
        completion = self._llm.complete(system_prompt, question)
        self._usage.record(user_id, completion.prompt_tokens, completion.completion_tokens)

        # citation_number coincide exactamente con el [N] que el LLM cita en el texto — mismo
        # enumerate() que arma _format_context(), así el frontend puede mostrar "[N]" en la
        # tarjeta sin adivinar el orden.
        citations = [
            Citation(
                message_id=item.message_id,
                channel_id=item.channel_id,
                sender_id=item.sender_id,
                content=_snippet(item.content),
                citation_number=i,
            )
            for i, item in enumerate(context_items, start=1)
        ]
        return CopilotAnswer(answer=completion.text, citations=citations)


def _format_context(items: list[RetrievedContext]) -> str:
    if not items:
        return "(sin resultados autorizados para esta pregunta)"
    # Timestamp explícito por mensaje: sin esto el LLM no puede distinguir "el horario original"
    # de "el horario que lo reemplazó" — ver regla 8 del prompt (copilot_v1.txt).
    return "\n".join(f"[{i}] ({item.created_at.strftime('%Y-%m-%d %H:%M')}) {item.content}" for i, item in enumerate(items, start=1))


_SNIPPET_MAX_LEN = 100


def _snippet(content: str) -> str:
    # La cita solo repite contenido que retrieve_ai_context() ya autorizó para ESTE usuario
    # (RLS aplicado antes de llegar aquí) — no es una fuga, es mostrarle al mismo usuario de
    # dónde salió la respuesta. Se trunca porque la tarjeta de cita es una vista previa, no el
    # mensaje completo (para eso el usuario puede abrir el canal).
    stripped = content.strip()
    if len(stripped) <= _SNIPPET_MAX_LEN:
        return stripped
    return stripped[:_SNIPPET_MAX_LEN].rstrip() + "…"
