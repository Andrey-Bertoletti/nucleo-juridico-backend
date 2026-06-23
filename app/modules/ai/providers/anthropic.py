"""Provedor Anthropic (Claude) — provedor de IA real.

Usa o SDK oficial `anthropic`. O modelo é configurável via `settings.AI_MODEL`
(default `claude-opus-4-8`, o modelo Opus mais capaz). A chave vem de
`settings.AI_API_KEY` (ou de ANTHROPIC_API_KEY no ambiente).

Escopo Fase 1: análise baseada em TEXTO (PDF/Word extraídos). Documentos que são
imagem/PDF escaneado chegam aqui como uma nota de OCR — leitura de imagem
(multimodal/visão) fica como evolução futura.
"""

import anthropic

from app.core.settings import settings
from app.modules.ai.prompts import SYSTEM_PROMPT, build_user_content
from app.modules.ai.providers.base import AIProvider, AIResult

DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 8000


class AnthropicProvider(AIProvider):
    def __init__(self) -> None:
        # api_key=None faz o SDK resolver do ambiente (ANTHROPIC_API_KEY).
        self._client = anthropic.Anthropic(api_key=settings.AI_API_KEY or None)
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

        message = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        # Refusal de segurança: trata sem quebrar (raro neste domínio jurídico).
        if message.stop_reason == "refusal":
            return AIResult(
                result_text=(
                    "A IA não pôde processar este documento por uma restrição de "
                    "segurança. Revise o conteúdo ou tente outra ação."
                ),
                model_used=message.model,
                tokens_input=message.usage.input_tokens,
                tokens_output=message.usage.output_tokens,
            )

        text = "".join(
            block.text for block in message.content if block.type == "text"
        ).strip()

        return AIResult(
            result_text=text or "(resposta vazia)",
            result_data=None,
            model_used=message.model,
            tokens_input=message.usage.input_tokens,
            tokens_output=message.usage.output_tokens,
        )
