"""Seleção do provedor de IA conforme `settings.AI_PROVIDER`.

Provedores disponíveis: `anthropic` (Claude, default), `openai` e `local` (stub).
Um valor desconhecido levanta erro claro — não há mais fallback silencioso.
"""

from app.core.settings import settings
from app.modules.ai.providers.base import AIProvider


def get_provider() -> AIProvider:
    name = (settings.AI_PROVIDER or "anthropic").strip().lower()

    if name == "anthropic":
        from app.modules.ai.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from app.modules.ai.providers.openai import OpenAIProvider

        return OpenAIProvider()
    if name in {"local", "ollama"}:
        from app.modules.ai.providers.local import LocalProvider

        return LocalProvider()

    raise ValueError(
        f"AI_PROVIDER desconhecido: {name!r}. Use 'anthropic', 'openai' ou 'local'."
    )
