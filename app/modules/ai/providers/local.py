"""Provedor LOCAL (Ollama) — PLACEHOLDER.

Implementação real fica pendente da DECISÃO DE PRIVACIDADE do cliente. Quando
liberado, este provedor:

  - chama um modelo aberto rodando localmente (ex.: via Ollama);
  - usa OCR local (Tesseract) para imagens, feito na camada de extração;
  - preenche `AIResult` da mesma forma que os demais.

Mantido como stub para não enviar código não testado para produção.
"""

from app.modules.ai.providers.base import AIProvider, AIResult


class LocalProvider(AIProvider):
    def run_action(
        self,
        *,
        action: str,
        document_text: str,
        documents: list[dict] | None = None,
        language: str = "pt-BR",
    ) -> AIResult:
        raise NotImplementedError(
            "Provedor de IA local ainda não configurado. Use AI_PROVIDER=anthropic "
            "(ou openai), ou implemente este provedor para rodar um modelo local."
        )
