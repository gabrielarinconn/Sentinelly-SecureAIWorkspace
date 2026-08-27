import psycopg

from backend.domain.entities import CopilotUsage
from backend.domain.ports import CopilotUsageRepository


class PsycopgCopilotUsageRepository(CopilotUsageRepository):
    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def record(self, user_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO rw_copilot_usage (user_id, prompt_tokens, completion_tokens) VALUES (%s, %s, %s)",
                (user_id, prompt_tokens, completion_tokens),
            )

    def get_for_actor(self) -> CopilotUsage:
        with self._conn.cursor() as cur:
            cur.execute("SELECT total_questions, total_prompt_tokens, total_completion_tokens FROM get_user_copilot_usage()")
            total_questions, total_prompt_tokens, total_completion_tokens = cur.fetchone()
        return CopilotUsage(
            total_questions=total_questions,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
        )
