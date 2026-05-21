"""Rotas do módulo orientations (inclui a fila /teacher/cases)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import (
    ROLE_ADMIN,
    ROLE_TEACHER,
    CurrentUser,
    DbSession,
)
from app.modules.attendances.schemas import AttendanceResponse
from app.modules.orientations import service
from app.modules.orientations.schemas import (
    OrientationCreate,
    OrientationResponse,
    OrientationUpdate,
    TeacherCaseItem,
)


router = APIRouter(tags=["teacher"])


# ---------------------------------------------------------------------------
# Fila do professor
# ---------------------------------------------------------------------------
@router.get("/teacher/cases", response_model=list[TeacherCaseItem])
def list_teacher_cases(
    db: DbSession,
    current_user: CurrentUser,
    legal_area_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    urgency: bool | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    search: str | None = Query(default=None),
    include_finished: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TeacherCaseItem]:
    if current_user.role == ROLE_TEACHER:
        teacher_filter: UUID | None = current_user.id  # type: ignore[assignment]
    elif current_user.role == ROLE_ADMIN:
        teacher_filter = None  # admin vê tudo
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas professores orientadores e a coordenação acessam esta lista.",
        )

    rows = service.list_teacher_cases(
        db,
        teacher_filter=teacher_filter,
        legal_area_id=legal_area_id,
        student_id=student_id,
        urgency=urgency,
        from_date=from_date,
        to_date=to_date,
        search=search,
        include_finished=include_finished,
        limit=limit,
        offset=offset,
    )
    return [TeacherCaseItem(**r) for r in rows]


@router.get("/teacher/cases/{attendance_id}", response_model=AttendanceResponse)
def get_teacher_case(
    attendance_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AttendanceResponse:
    if current_user.role not in {ROLE_TEACHER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas professores orientadores e a coordenação acessam esta área.",
        )
    return service.get_teacher_case(db, attendance_id, current_user)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Orientations CRUD
# ---------------------------------------------------------------------------
@router.get(
    "/attendances/{attendance_id}/orientations",
    response_model=list[OrientationResponse],
)
def list_orientations(
    attendance_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[OrientationResponse]:
    return service.list_orientations(db, attendance_id)  # type: ignore[return-value]


@router.post(
    "/attendances/{attendance_id}/orientation",
    response_model=OrientationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_orientation(
    attendance_id: UUID,
    payload: OrientationCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> OrientationResponse:
    return service.create_orientation(
        db, attendance_id, payload, current_user
    )  # type: ignore[return-value]


@router.patch(
    "/orientations/{orientation_id}", response_model=OrientationResponse
)
def update_orientation(
    orientation_id: UUID,
    payload: OrientationUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> OrientationResponse:
    return service.update_orientation(
        db, orientation_id, payload, current_user
    )  # type: ignore[return-value]
