"""Regras de negócio do módulo appointments."""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import Date, Integer, String, Uuid, bindparam, text
from sqlalchemy.orm import Session

from app.core.dependencies import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from app.modules.appointments.models import Appointment
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)
from app.modules.attendances.models import Attendance, AttendanceHistory
from app.modules.users.models import Profile


APPOINTMENT_STATUS_LABELS: dict[str, str] = {
    "agendado": "agendado",
    "confirmado": "confirmado",
    "compareceu": "compareceu",
    "nao_compareceu": "não compareceu",
    "remarcado": "remarcado",
    "cancelado": "cancelado",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _scope_clause_for(user: Profile) -> tuple[str, dict[str, Any]]:
    """Devolve o trecho SQL do WHERE para limitar o que o usuário pode ver.

    - admin: sem filtro
    - aluno: appointments cujo `responsible_id` seja o próprio, OU o
      atendimento vinculado tenha `student_id` igual ao próprio.
    - professor: appointments cujo `responsible_id` seja o próprio, OU o
      atendimento vinculado tenha `teacher_id` igual ao próprio.
    """
    if user.role == ROLE_ADMIN:
        return "", {}

    if user.role == ROLE_STUDENT:
        return (
            "and ("
            "  ap.responsible_id = :scope_user_id "
            "  or exists (select 1 from attendances a "
            "             where a.id = ap.attendance_id "
            "               and a.student_id = :scope_user_id)"
            ")"
        ), {"scope_user_id": str(user.id)}

    if user.role == ROLE_TEACHER:
        return (
            "and ("
            "  ap.responsible_id = :scope_user_id "
            "  or exists (select 1 from attendances a "
            "             where a.id = ap.attendance_id "
            "               and a.teacher_id = :scope_user_id)"
            ")"
        ), {"scope_user_id": str(user.id)}

    # Outros perfis (não previstos): nada
    return "and false", {}


def _record_history(
    db: Session,
    *,
    attendance_id: UUID | None,
    user_id: UUID | None,
    event_type: str,
    description: str,
) -> None:
    if attendance_id is None:
        return
    db.add(
        AttendanceHistory(
            attendance_id=attendance_id,
            user_id=user_id,
            event_type=event_type,
            description=description,
        )
    )


def _can_modify(user: Profile, appointment: Appointment) -> bool:
    if user.role == ROLE_ADMIN:
        return True
    if appointment.responsible_id == user.id:
        return True
    # Professor responsável pelo atendimento vinculado também pode
    if user.role == ROLE_TEACHER and appointment.attendance_id is not None:
        # carregado pela query no service — simplificação: deixa o router checar
        pass
    return False


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def list_appointments(
    db: Session,
    current_user: Profile,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    responsible_id: UUID | None = None,
    status_filter: str | None = None,
    client_id: UUID | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    scope_sql, scope_params = _scope_clause_for(current_user)

    sql = text(
        f"""
        select
          ap.id,
          ap.client_id,
          c.full_name                       as client_name,
          ap.attendance_id,
          ap.responsible_id,
          p.name                            as responsible_name,
          ap.appointment_date,
          ap.appointment_time,
          ap.reason,
          ap.status,
          ap.notes,
          ap.created_at,
          ap.updated_at
        from appointments ap
        join clients c        on c.id = ap.client_id
        left join profiles p  on p.id = ap.responsible_id
        where (:from_date is null or ap.appointment_date >= :from_date)
          and (:to_date is null   or ap.appointment_date <= :to_date)
          and (:responsible_id is null or ap.responsible_id = :responsible_id)
          and (:status_filter is null or ap.status = :status_filter)
          and (:client_id is null or ap.client_id = :client_id)
          {scope_sql}
        order by ap.appointment_date asc,
                 ap.appointment_time asc nulls last,
                 ap.created_at asc
        limit :limit offset :offset
        """
    ).bindparams(
        bindparam("from_date", type_=Date),
        bindparam("to_date", type_=Date),
        bindparam("responsible_id", type_=Uuid),
        bindparam("status_filter", type_=String),
        bindparam("client_id", type_=Uuid),
        bindparam("limit", type_=Integer),
        bindparam("offset", type_=Integer),
    )

    rows = db.execute(
        sql,
        {
            "from_date": from_date,
            "to_date": to_date,
            "responsible_id": responsible_id,
            "status_filter": status_filter,
            "client_id": client_id,
            "limit": limit,
            "offset": offset,
            **scope_params,
        },
    ).mappings().all()
    return [dict(r) for r in rows]


def get_appointment(
    db: Session, appointment_id: UUID, current_user: Profile
) -> Appointment:
    appt = (
        db.query(Appointment).filter(Appointment.id == appointment_id).one_or_none()
    )
    if appt is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Retorno não encontrado.",
        )
    _ensure_can_view(appt, current_user, db)
    return appt


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------
def _attendance_for(appt: Appointment, db: Session) -> Attendance | None:
    if appt.attendance_id is None:
        return None
    return (
        db.query(Attendance)
        .filter(Attendance.id == appt.attendance_id)
        .one_or_none()
    )


def _ensure_can_view(appt: Appointment, user: Profile, db: Session) -> None:
    if user.role == ROLE_ADMIN:
        return
    if appt.responsible_id == user.id:
        return
    attendance = _attendance_for(appt, db)
    if attendance is None:
        # sem vínculo: só responsável vê
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Acesso negado.",
        )
    if user.role == ROLE_STUDENT and attendance.student_id == user.id:
        return
    if user.role == ROLE_TEACHER and attendance.teacher_id == user.id:
        return
    raise HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Acesso negado.",
    )


def _ensure_can_modify(appt: Appointment, user: Profile, db: Session) -> None:
    if user.role == ROLE_ADMIN:
        return
    if appt.responsible_id == user.id:
        return
    attendance = _attendance_for(appt, db)
    if attendance is not None:
        if user.role == ROLE_TEACHER and attendance.teacher_id == user.id:
            return
        if user.role == ROLE_STUDENT and attendance.student_id == user.id:
            return
    raise HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Apenas o responsável (ou um vinculado ao atendimento) pode alterar este retorno.",
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def create_appointment(
    db: Session, payload: AppointmentCreate, current_user: Profile
) -> Appointment:
    if current_user.role not in {ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para agendar retornos.",
        )

    responsible = payload.responsible_id or current_user.id

    appt = Appointment(
        client_id=payload.client_id,
        attendance_id=payload.attendance_id,
        responsible_id=responsible,
        appointment_date=payload.appointment_date,
        appointment_time=payload.appointment_time,
        reason=payload.reason,
        notes=payload.notes,
        status="agendado",
    )
    db.add(appt)
    db.flush()

    _record_history(
        db,
        attendance_id=payload.attendance_id,
        user_id=current_user.id,
        event_type="agendamento",
        description=(
            f"Retorno agendado por {current_user.name} para "
            f"{payload.appointment_date.isoformat()}"
            + (
                f" às {payload.appointment_time.strftime('%H:%M')}"
                if payload.appointment_time
                else ""
            )
            + "."
        ),
    )

    db.commit()
    db.refresh(appt)
    return appt


def update_appointment(
    db: Session,
    appointment_id: UUID,
    payload: AppointmentUpdate,
    current_user: Profile,
) -> Appointment:
    appt = (
        db.query(Appointment).filter(Appointment.id == appointment_id).one_or_none()
    )
    if appt is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Retorno não encontrado.",
        )
    _ensure_can_modify(appt, current_user, db)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return appt

    changed_date = "appointment_date" in data and data["appointment_date"] != appt.appointment_date
    changed_time = "appointment_time" in data and data["appointment_time"] != appt.appointment_time

    for field, value in data.items():
        setattr(appt, field, value)

    if changed_date or changed_time:
        # Se a data/hora mudou, marca como remarcado (a menos que admin force outro status depois).
        appt.status = "remarcado"

    _record_history(
        db,
        attendance_id=appt.attendance_id,
        user_id=current_user.id,
        event_type="observacao",
        description=f"Retorno atualizado por {current_user.name}.",
    )

    db.commit()
    db.refresh(appt)
    return appt


def change_status(
    db: Session,
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    current_user: Profile,
) -> Appointment:
    appt = (
        db.query(Appointment).filter(Appointment.id == appointment_id).one_or_none()
    )
    if appt is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Retorno não encontrado.",
        )
    _ensure_can_modify(appt, current_user, db)

    if appt.status == payload.status:
        return appt

    old_status = appt.status
    appt.status = payload.status

    event_type = "retorno" if payload.status == "compareceu" else "observacao"
    description = (
        payload.note
        or (
            f"Status do retorno alterado de '{APPOINTMENT_STATUS_LABELS[old_status]}' "
            f"para '{APPOINTMENT_STATUS_LABELS[payload.status]}' por {current_user.name}."
        )
    )
    _record_history(
        db,
        attendance_id=appt.attendance_id,
        user_id=current_user.id,
        event_type=event_type,
        description=description,
    )

    db.commit()
    db.refresh(appt)
    return appt


def delete_appointment(
    db: Session, appointment_id: UUID, current_user: Profile
) -> Appointment | None:
    """Soft-delete (status='cancelado') se houver vínculo com atendimento;
    hard-delete se for um retorno avulso.

    Em ambos os casos registra histórico se houver atendimento vinculado.
    """
    appt = (
        db.query(Appointment).filter(Appointment.id == appointment_id).one_or_none()
    )
    if appt is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Retorno não encontrado.",
        )
    _ensure_can_modify(appt, current_user, db)

    if appt.attendance_id is not None:
        # Soft: marca como cancelado
        if appt.status != "cancelado":
            appt.status = "cancelado"
        _record_history(
            db,
            attendance_id=appt.attendance_id,
            user_id=current_user.id,
            event_type="observacao",
            description=f"Retorno cancelado por {current_user.name}.",
        )
        db.commit()
        db.refresh(appt)
        return appt

    # Sem vínculo: hard-delete
    db.delete(appt)
    db.commit()
    return None
