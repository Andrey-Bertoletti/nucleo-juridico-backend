"""Rotas do módulo reports."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbSession
from app.modules.attendances.schemas import AttendanceListItem
from app.modules.reports import service
from app.modules.reports.schemas import (
    AreaCount,
    DashboardCounters,
    DashboardResponse,
    ProductivityRow,
    ReportsSummary,
    StatusCount,
)


router = APIRouter(tags=["reports"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
) -> DashboardResponse:
    data = service.get_dashboard(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
    )
    return DashboardResponse(
        role=data["role"],
        period_from=data["period_from"],
        period_to=data["period_to"],
        total=data["total"],
        counters=DashboardCounters(**data["counters"]),
        urgentes=data["urgentes"],
        appointments_today=data["appointments_today"],
        pending_documents=data["pending_documents"],
        pending_teacher_analysis=data["pending_teacher_analysis"],
    )


@router.get("/reports/summary", response_model=ReportsSummary)
def reports_summary(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    teacher_id: UUID | None = Query(default=None),
) -> ReportsSummary:
    data = service.get_summary(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    return ReportsSummary(
        role=data["role"],
        period_from=data["period_from"],
        period_to=data["period_to"],
        total=data["total"],
        counters=DashboardCounters(**data["counters"]),
        urgentes=data["urgentes"],
    )


@router.get("/reports/by-status", response_model=list[StatusCount])
def reports_by_status(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    teacher_id: UUID | None = Query(default=None),
) -> list[StatusCount]:
    rows = service.by_status(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    return [StatusCount(**r) for r in rows]


@router.get("/reports/by-area", response_model=list[AreaCount])
def reports_by_area(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    student_id: UUID | None = Query(default=None),
    teacher_id: UUID | None = Query(default=None),
) -> list[AreaCount]:
    rows = service.by_area(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    return [AreaCount(**r) for r in rows]


@router.get("/reports/by-student", response_model=list[ProductivityRow])
def reports_by_student(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
) -> list[ProductivityRow]:
    rows = service.by_user(
        db,
        current_user,
        join_field="student_id",
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
    )
    return [ProductivityRow(**r) for r in rows]


@router.get("/reports/by-teacher", response_model=list[ProductivityRow])
def reports_by_teacher(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
) -> list[ProductivityRow]:
    rows = service.by_user(
        db,
        current_user,
        join_field="teacher_id",
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
    )
    return [ProductivityRow(**r) for r in rows]


@router.get(
    "/reports/pending-documents", response_model=list[AttendanceListItem]
)
def reports_pending_documents(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AttendanceListItem]:
    rows = service.pending_documents(
        db, current_user, limit=limit, offset=offset
    )
    return [AttendanceListItem(**r) for r in rows]


@router.get(
    "/reports/pending-teacher-analysis",
    response_model=list[AttendanceListItem],
)
def reports_pending_analysis(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AttendanceListItem]:
    rows = service.pending_teacher_analysis(
        db, current_user, limit=limit, offset=offset
    )
    return [AttendanceListItem(**r) for r in rows]
