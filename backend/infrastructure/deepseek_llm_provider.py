import os

from openai import OpenAI

from backend.domain.entities import LLMCompletion
from backend.domain.ports import LLMProvider


class DeepSeekLLMProvider(LLMProvider):
    """Proveedor real de LLM (Fase 18, D007). DeepSeek expone una API compatible con el SDK
    de OpenAI (mismo cliente, distinto base_url) — no se importa ningún SDK propio de
    DeepSeek, así que cambiar de proveedor en el futuro es solo escribir otra clase."""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self._model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

    def complete(self, system_prompt: str, user_prompt: str) -> LLMCompletion:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        usage = response.usage
        return LLMCompletion(
            text=response.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
