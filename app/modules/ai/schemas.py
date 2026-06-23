"""Schemas Pydantic do módulo ai."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Ações por documento + a ação `analise_geral` (escopo de cliente).
AIAction = Literal[
    "resumo",
    "pontos_chave",
    "prazos",
    "partes",
    "valores",
    "detalhes",
    "riscos",
    "classificacao",
    "analise_geral",
]

# Ações válidas no escopo de um único documento (exclui a geral).
DOCUMENT_ACTIONS: tuple[str, ...] = (
    "resumo",
    "pontos_chave",
    "prazos",
    "partes",
    "valores",
    "detalhes",
    "riscos",
    "classificacao",
)

AIStatus = Literal["processando", "pronto", "erro"]
AIScope = Literal["document", "client"]


class AIAnalysisRequest(BaseModel):
    """Corpo opcional do POST. `force=true` ignora o cache e refaz a análise."""

    force: bool = False


class AIAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: AIScope
    document_id: UUID | None
    client_id: UUID | None
    action: AIAction
    status: AIStatus
    result_text: str | None
    result_data: dict | None
    model_used: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
