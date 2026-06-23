"""Interface abstrata do provedor de IA.

Esta é a peça que blinda o sistema da decisão de privacidade: toda a lógica de
negócio fala apenas com `AIProvider`, nunca com um SDK específico. Trocar de
provedor = trocar a implementação concreta, sem mexer no resto.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResult:
    """Resultado padronizado de uma ação de IA."""

    result_text: str
    result_data: dict | None = None
    model_used: str = "desconhecido"
    tokens_input: int = 0
    tokens_output: int = 0


class AIProvider(ABC):
    @abstractmethod
    def run_action(
        self,
        *,
        action: str,
        document_text: str,
        documents: list[dict] | None = None,
        language: str = "pt-BR",
    ) -> AIResult:
        """Executa uma ação.

        - Ações de documento: usa `document_text`.
        - Ação `analise_geral`: usa `documents` (lista de
          ``{document_id, file_name, document_type, text}``).
        """
        raise NotImplementedError
