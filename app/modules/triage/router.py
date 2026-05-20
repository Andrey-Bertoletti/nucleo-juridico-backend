"""Rotas do módulo triage (sob /attendances/{id}/triage)."""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.triage import service
from app.modules.triage.schemas import TriageCreate, TriageResponse, TriageUpdate


router = APIRouter(
    prefix="/attendances/{attendance_id}/triage",
    tags=["triage"],
)


@router.post(
    "",
    response_model=TriageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_triage(
    attendance_id: UUID,
    payload: TriageCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> TriageResponse:
    return service.create_triage(db, attendance_id, payload, current_user)  # type: ignore[return-value]


@router.get("", response_model=TriageResponse)
def get_triage(
    attendance_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> TriageResponse:
    return service.get_triage(db, attendance_id)  # type: ignore[return-value]


@router.patch("", response_model=TriageResponse)
def update_triage(
    attendance_id: UUID,
    payload: TriageUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> TriageResponse:
    return service.update_triage(db, attendance_id, payload, current_user)  # type: ignore[return-value]
