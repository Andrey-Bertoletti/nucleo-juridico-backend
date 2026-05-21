"""Regras de negócio do módulo orientations."""

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import Boolean, Date, Integer, String, Uuid, bindparam, text
from sqlalchemy.orm import Session

from app.core.dependencies import ROLE_ADMIN, ROLE_TEACHER
from app.modules.attendances.models import Attendance, AttendanceHistory
from app.modules.orientations.models import Orientation
from app.modules.orientations.schemas import (
    OrientationCreate,
    OrientationUpdate,
)
from app.modules.users.models import Profile


DECISION_TO_STATUS: dict[str, str] = {
    "solicitar_correcao": "correcao_solicitada",
    "solicitar_documentos": "aguardando_documentos",
    "aprovar_encaminhamento": "encaminhamento_aprovado",
    "finalizar_atendimento": "finalizado",
}

DECISION_LABELS: dict[str, str] = {
    "solicitar_correcao": "Solicitação de correção",
    "solicitar_documentos": "Solicitação de documentos",
    "aprovar_encaminhamento": "Aprovação de encaminhamento",
    "finalizar_atendimento": "Finalização do atendimento",
}


def _get_attendance(db: Session, attendance_id: UUID) -> Attendance:
    a = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .one_or_none()
    )
    if a is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado.",
        )
    return a


def _ensure_teacher_or_admin(user: Profile) -> None:
    if user.role not in {ROLE_TEACHER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Apenas professores orientadores e a coordenação podem registrar orientações.",
        )


def _ensure_teacher_access(attendance: Attendance, user: Profile) -> None:
    """Professor só acessa casos atribuídos a ele; admin acessa todos."""
    if user.role == ROLE_ADMIN:
        return
    if user.role != ROLE_TEACHER:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Acesso negado.",
        )
    if attendance.teacher_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Este caso não está sob sua orientação.",
        )


def _record_history(
    db: Session,
    *,
    attendance_id: UUID,
    user_id: UUID | None,
    event_type: str,
    description: str,
    old_status: str | None = None,
    new_status: str | None = None,
) -> None:
    db.add(
        AttendanceHistory(
            attendance_id=attendance_id,
            user_id=user_id,
            event_type=event_type,
            description=description,
            old_status=old_status,
            new_status=new_status,
        )
    )


# ---------------------------------------------------------------------------
# Queries — fila de casos do professor
# ---------------------------------------------------------------------------
def list_teacher_cases(
    db: Session,
    *,
    teacher_filter: UUID | None,
    legal_area_id: UUID | None = None,
    student_id: UUID | None = None,
    urgency: bool | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    search: str | None = None,
    include_finished: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = text(
        """
        select
          a.id,
          a.client_id,
          c.full_name                    as client_name,
          a.legal_area_id,
          la.name                        as legal_area_name,
          a.student_id,
          s.name                         as student_name,
          a.status,
          a.urgency,
          a.created_at,
          a.updated_at
        from attendances a
        join clients c                   on c.id  = a.client_id
        left join legal_areas la         on la.id = a.legal_area_id
        left join profiles s             on s.id  = a.student_id
        where (:teacher_filter is null or a.teacher_id = :teacher_filter)
          and (
                :include_finished = true
                or a.status not in ('finalizado', 'arquivado')
              )
          and (:legal_area_id is null   or a.legal_area_id = :legal_area_id)
          and (:student_id is null      or a.student_id    = :student_id)
          and (cast(:urgency as boolean) is null
               or a.urgency = cast(:urgency as boolean))
          and (:from_date is null       or a.created_at   >= :from_date)
          and (:to_date is null         or a.created_at   <= :to_date)
          and (:search is null          or c.full_name ilike :search_pat)
        order by a.urgency desc, a.created_at desc
        limit :limit offset :offset
        """
    ).bindparams(
        bindparam("teacher_filter", type_=Uuid),
        bindparam("include_finished", type_=Boolean),
        bindparam("legal_area_id", type_=Uuid),
        bindparam("student_id", type_=Uuid),
        bindparam("from_date", type_=Date),
        bindparam("to_date", type_=Date),
        bindparam("search", type_=String),
        bindparam("search_pat", type_=String),
        bindparam("limit", type_=Integer),
        bindparam("offset", type_=Integer),
    )

    rows = db.execute(
        sql,
        {
            "teacher_filter": teacher_filter,
            "include_finished": include_finished,
            "legal_area_id": legal_area_id,
            "student_id": student_id,
            "urgency": urgency,
            "from_date": from_date,
            "to_date": to_date,
            "search": search,
            "search_pat": f"%{search}%" if search else None,
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()
    return [dict(r) for r in rows]


def get_teacher_case(
    db: Session, attendance_id: UUID, current_user: Profile
) -> Attendance:
    attendance = _get_attendance(db, attendance_id)
    _ensure_teacher_access(attendance, current_user)
    return attendance


# ---------------------------------------------------------------------------
# Orientations
# ---------------------------------------------------------------------------
def list_orientations(
    db: Session, attendance_id: UUID
) -> list[Orientation]:
    _get_attendance(db, attendance_id)
    return (
        db.query(Orientation)
        .filter(Orientation.attendance_id == attendance_id)
        .order_by(Orientation.created_at.desc())
        .all()
    )


def create_orientation(
    db: Session,
    attendance_id: UUID,
    payload: OrientationCreate,
    current_user: Profile,
) -> Orientation:
    _ensure_teacher_or_admin(current_user)
    attendance = _get_attendance(db, attendance_id)

    # Professor só registra orientação em casos atribuídos a ele
    if (
        current_user.role == ROLE_TEACHER
        and attendance.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Este caso não está sob sua orientação.",
        )

    orientation = Orientation(
        attendance_id=attendance_id,
        teacher_id=current_user.id,
        orientation_text=payload.orientation_text,
        teacher_notes=payload.teacher_notes,
        decision=payload.decision,
    )
    db.add(orientation)
    db.flush()

    description_base = (
        f"Orientação registrada por {current_user.name}"
    )

    # Histórico do evento "orientação"
    _record_history(
        db,
        attendance_id=attendance_id,
        user_id=current_user.id,
        event_type="orientacao",
        description=description_base + (
            f" — decisão: {DECISION_LABELS[payload.decision]}."
            if payload.decision
            else " (sem decisão de status)."
        ),
    )

    # Aplicar transição de status com base na decisão
    if payload.decision:
        old_status = attendance.status
        new_status = DECISION_TO_STATUS[payload.decision]
        if old_status != new_status:
            attendance.status = new_status
            if new_status == "finalizado" and attendance.finished_at is None:
                attendance.finished_at = datetime.now(timezone.utc)
            elif new_status != "finalizado":
                attendance.finished_at = None

            event_type = (
                "encerramento"
                if new_status == "finalizado"
                else "mudanca_status"
            )
            _record_history(
                db,
                attendance_id=attendance_id,
                user_id=current_user.id,
                event_type=event_type,
                description=(
                    f"Status alterado por {current_user.name} a partir da decisão "
                    f"'{DECISION_LABELS[payload.decision]}'."
                ),
                old_status=old_status,
                new_status=new_status,
            )

    db.commit()
    db.refresh(orientation)
    return orientation


def update_orientation(
    db: Session,
    orientation_id: UUID,
    payload: OrientationUpdate,
    current_user: Profile,
) -> Orientation:
    _ensure_teacher_or_admin(current_user)

    orientation = (
        db.query(Orientation)
        .filter(Orientation.id == orientation_id)
        .one_or_none()
    )
    if orientation is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Orientação não encontrada.",
        )

    # Professor só edita as próprias orientações; admin edita qualquer
    if (
        current_user.role == ROLE_TEACHER
        and orientation.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Só é possível editar orientações registradas por você.",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return orientation

    for field, value in data.items():
        setattr(orientation, field, value)

    _record_history(
        db,
        attendance_id=orientation.attendance_id,
        user_id=current_user.id,
        event_type="observacao",
        description=f"Orientação editada por {current_user.name}.",
    )

    db.commit()
    db.refresh(orientation)
    return orientation
