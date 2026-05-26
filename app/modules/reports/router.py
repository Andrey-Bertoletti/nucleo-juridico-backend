"""Rotas do módulo reports."""

from datetime import date
from uuid import UUID

import io

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DbSession
from app.modules.attendances.schemas import AttendanceListItem
from app.modules.reports import service
from app.modules.reports.export import generate_excel, generate_pdf
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


# ---------------------------------------------------------------------------
# Exportação de relatórios
# ---------------------------------------------------------------------------

def _fetch_report_data(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None,
    period_to: date | None,
    legal_area_id: UUID | None,
    student_id: UUID | None,
    teacher_id: UUID | None,
) -> tuple[dict, list, list, list, list]:
    """Busca todos os dados necessários para gerar o relatório exportado."""
    summary_data = service.get_summary(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    status_data = service.by_status(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    area_data = service.by_area(
        db,
        current_user,
        period_from=period_from,
        period_to=period_to,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    student_data = service.by_user(
        db,
        current_user,
        join_field="student_id",
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
    )
    teacher_data = service.by_user(
        db,
        current_user,
        join_field="teacher_id",
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
    )
    return summary_data, status_data, area_data, student_data, teacher_data


@router.get("/reports/export/pdf")
def export_pdf(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    teacher_id: UUID | None = Query(default=None),
) -> StreamingResponse:
    summary_data, status_data, area_data, student_data, teacher_data = (
        _fetch_report_data(
            db, current_user, period_from, period_to,
            legal_area_id, student_id, teacher_id,
        )
    )

    pdf_bytes = generate_pdf(
        summary_data, status_data, area_data,
        student_data, teacher_data,
        period_from, period_to,
    )

    filename = f"relatorio_nucleo_juridico_{date.today().isoformat()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/export/excel")
def export_excel(
    db: DbSession,
    current_user: CurrentUser,
    period_from: date | None = Query(default=None, alias="from"),
    period_to: date | None = Query(default=None, alias="to"),
    legal_area_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    teacher_id: UUID | None = Query(default=None),
) -> StreamingResponse:
    summary_data, status_data, area_data, student_data, teacher_data = (
        _fetch_report_data(
            db, current_user, period_from, period_to,
            legal_area_id, student_id, teacher_id,
        )
    )

    excel_bytes = generate_excel(
        summary_data, status_data, area_data,
        student_data, teacher_data,
        period_from, period_to,
    )

    filename = f"relatorio_nucleo_juridico_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
