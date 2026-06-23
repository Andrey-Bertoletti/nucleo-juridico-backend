"""Provedor OpenAI — provedor de IA real (alternativa à Anthropic).

Usa o SDK oficial `openai`. O modelo é configurável via `settings.AI_MODEL`
(defina explicitamente, ex.: `gpt-4o`). A chave vem de `settings.AI_API_KEY`
(ou de OPENAI_API_KEY no ambiente).

Escopo Fase 1: análise baseada em TEXTO (PDF/Word extraídos). Leitura de imagem
(visão) fica como evolução futura.
"""

from openai import OpenAI

from app.core.settings import settings
from app.modules.ai.prompts import SYSTEM_PROMPT, build_user_content
from app.modules.ai.providers.base import AIProvider, AIResult

DEFAULT_MODEL = "gpt-4o"
MAX_TOKENS = 8000


class OpenAIProvider(AIProvider):
    def __init__(self) -> None:
        # api_key=None faz o SDK resolver do ambiente (OPENAI_API_KEY).
        self._client = OpenAI(api_key=settings.AI_API_KEY or None)
        self._model = settings.AI_MODEL or DEFAULT_MODEL

    def run_action(
        self,
        *,
        action: str,
        document_text: str,
        documents: list[dict] | None = None,
        language: str = "pt-BR",
    ) -> AIResult:
        user_content = build_user_content(action, document_text, documents)

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        text = (response.choices[0].message.content or "").strip()
        usage = response.usage

        return AIResult(
            result_text=text or "(resposta vazia)",
            result_data=None,
            model_used=response.model,
            tokens_input=usage.prompt_tokens if usage else 0,
            tokens_output=usage.completion_tokens if usage else 0,
        )
