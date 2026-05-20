"""Rotas do módulo attendances."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    CurrentUser,
    DbSession,
)
from app.modules.attendances import service
from app.modules.attendances.schemas import (
    AttendanceCreate,
    AttendanceHistoryItem,
    AttendanceListItem,
    AttendanceResponse,
    AttendanceStatusUpdate,
    AttendanceUpdate,
    SendToTeacherRequest,
)
from app.modules.users.models import Profile


router = APIRouter(prefix="/attendances", tags=["attendances"])


# Aluno e admin podem criar/encaminhar atendimentos. Professor é leitura
# + analisar (mudar status quando responsável).
def require_attendance_creator(current_user: CurrentUser) -> Profile:
    if current_user.role not in {ROLE_STUDENT, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas alunos/estagiários e coordenação podem criar atendimentos.",
        )
    return current_user


AttendanceCreator = Annotated[Profile, Depends(require_attendance_creator)]


@router.get("", response_model=list[AttendanceListItem])
def list_attendances(
    db: DbSession,
    _current: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
    legal_area_id: UUID | None = Query(default=None),
    demand_type_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    teacher_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    urgency: bool | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    search: str | None = Query(default=None, description="Busca por nome do cliente."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AttendanceListItem]:
    rows = service.list_attendances(
        db,
        status_filter=status_filter,
        legal_area_id=legal_area_id,
        demand_type_id=demand_type_id,
        student_id=student_id,
        teacher_id=teacher_id,
        client_id=client_id,
        urgency=urgency,
        from_date=from_date,
        to_date=to_date,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [AttendanceListItem(**r) for r in rows]


@router.post(
    "",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance(
    payload: AttendanceCreate,
    db: DbSession,
    current_user: AttendanceCreator,
) -> AttendanceResponse:
    return service.create_attendance(db, payload, current_user)  # type: ignore[return-value]


@router.get("/{attendance_id}", response_model=AttendanceResponse)
def get_attendance(
    attendance_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> AttendanceResponse:
    return service.get_attendance(db, attendance_id)  # type: ignore[return-value]


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: UUID,
    payload: AttendanceUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AttendanceResponse:
    return service.update_attendance(db, attendance_id, payload, current_user)  # type: ignore[return-value]


@router.patch("/{attendance_id}/status", response_model=AttendanceResponse)
def change_attendance_status(
    attendance_id: UUID,
    payload: AttendanceStatusUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AttendanceResponse:
    return service.change_status(db, attendance_id, payload, current_user)  # type: ignore[return-value]


@router.post("/{attendance_id}/send-to-teacher", response_model=AttendanceResponse)
def send_attendance_to_teacher(
    attendance_id: UUID,
    payload: SendToTeacherRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> AttendanceResponse:
    return service.send_to_teacher(db, attendance_id, payload, current_user)  # type: ignore[return-value]


@router.get(
    "/{attendance_id}/history", response_model=list[AttendanceHistoryItem]
)
def get_attendance_history(
    attendance_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[AttendanceHistoryItem]:
    return service.list_history(db, attendance_id)  # type: ignore[return-value]
