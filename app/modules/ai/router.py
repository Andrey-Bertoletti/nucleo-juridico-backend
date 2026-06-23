"""Rotas do módulo ai — Análise com IA (Fase 1)."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.ai import service
from app.modules.ai.schemas import (
    DOCUMENT_ACTIONS,
    AIAnalysisRequest,
    AIAnalysisResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _validate_document_action(action: str) -> None:
    if action not in DOCUMENT_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ação inválida para documento: {action}",
        )


# ---------------------------------------------------------------------------
# Ações por documento
# ---------------------------------------------------------------------------
@router.post(
    "/documents/{document_id}/actions/{action}",
    response_model=AIAnalysisResponse,
)
def run_document_action(
    document_id: UUID,
    action: str,
    db: DbSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    payload: AIAnalysisRequest | None = None,
) -> AIAnalysisResponse:
    _validate_document_action(action)
    force = payload.force if payload else False
    row = service.trigger_document_action(
        db,
        document_id=document_id,
        action=action,
        force=force,
        user=current_user,
        background_tasks=background_tasks,
    )
    return row  # type: ignore[return-value]


@router.get(
    "/documents/{document_id}/actions/{action}",
    response_model=AIAnalysisResponse,
)
def get_document_action(
    document_id: UUID,
    action: str,
    db: DbSession,
    _current: CurrentUser,
) -> AIAnalysisResponse:
    _validate_document_action(action)
    return service.get_document_action(db, document_id, action)  # type: ignore[return-value]


@router.get(
    "/documents/{document_id}/analyses",
    response_model=list[AIAnalysisResponse],
)
def list_document_analyses(
    document_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[AIAnalysisResponse]:
    return service.list_document_analyses(db, document_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Análise geral (cliente)
# ---------------------------------------------------------------------------
@router.post(
    "/clients/{client_id}/general-report",
    response_model=AIAnalysisResponse,
)
def run_general_report(
    client_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    payload: AIAnalysisRequest | None = None,
) -> AIAnalysisResponse:
    force = payload.force if payload else False
    row = service.trigger_general_report(
        db,
        client_id=client_id,
        force=force,
        user=current_user,
        background_tasks=background_tasks,
    )
    return row  # type: ignore[return-value]


@router.get(
    "/clients/{client_id}/general-report",
    response_model=AIAnalysisResponse,
)
def get_general_report(
    client_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> AIAnalysisResponse:
    return service.get_general_report(db, client_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Polling por id
# ---------------------------------------------------------------------------
@router.get("/analyses/{analysis_id}", response_model=AIAnalysisResponse)
def get_analysis(
    analysis_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> AIAnalysisResponse:
    return service.get_analysis(db, analysis_id)  # type: ignore[return-value]
