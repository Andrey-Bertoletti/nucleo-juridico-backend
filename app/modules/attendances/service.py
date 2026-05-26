"""Regras de negócio do módulo attendances."""

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import Boolean, Date, Integer, String, Uuid, bindparam, text
from sqlalchemy.orm import Session

from app.core.dependencies import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from app.modules.attendances.models import Attendance, AttendanceHistory
from app.modules.attendances.schemas import (
    AttendanceCreate,
    AttendanceStatusUpdate,
    AttendanceUpdate,
    SendToTeacherRequest,
)
from app.modules.users.models import Profile


FINAL_STATUSES = {"finalizado", "arquivado"}
TEACHER_HANDLING_STATUSES = {
    "encaminhado_ao_professor",
    "em_analise_pelo_professor",
    "correcao_solicitada",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _record_history(
    db: Session,
    *,
    attendance_id: UUID,
    user_id: UUID | None,
    event_type: str,
    description: str | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
) -> None:
    entry = AttendanceHistory(
        attendance_id=attendance_id,
        user_id=user_id,
        event_type=event_type,
        description=description,
        old_status=old_status,
        new_status=new_status,
    )
    db.add(entry)


def _ensure_can_edit(attendance: Attendance, user: Profile) -> None:
    """Aluno só edita enquanto não estiver finalizado; admin sempre pode."""
    if user.role == ROLE_ADMIN:
        return
    if user.role == ROLE_STUDENT:
        if attendance.status in FINAL_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Atendimento finalizado — apenas a coordenação pode editar.",
            )
        return
    raise HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Você não tem permissão para editar este atendimento.",
    )


def _ensure_can_change_status(
    attendance: Attendance, user: Profile, new_status: str
) -> None:
    if user.role == ROLE_ADMIN:
        return
    if user.role == ROLE_STUDENT:
        if attendance.status in FINAL_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Atendimento finalizado — aluno não pode alterar status.",
            )
        return
    if user.role == ROLE_TEACHER:
        # Professor pode mover apenas atendimentos sob sua responsabilidade
        # e enquanto estão na fase de análise.
        if attendance.teacher_id != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Você só pode analisar atendimentos encaminhados a você.",
            )
        if attendance.status not in TEACHER_HANDLING_STATUSES and (
            new_status not in TEACHER_HANDLING_STATUSES.union(
                {"encaminhamento_aprovado", "finalizado"}
            )
        ):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Transição de status não permitida para o perfil professor.",
            )
        return
    raise HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para alterar status.",
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def list_attendances(
    db: Session,
    *,
    status_filter: str | None = None,
    legal_area_id: UUID | None = None,
    demand_type_id: UUID | None = None,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
    client_id: UUID | None = None,
    urgency: bool | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = text(
        """
        select
          a.id,
          a.client_id,
          c.full_name                            as client_name,
          a.legal_area_id,
          la.name                                as legal_area_name,
          a.demand_type_id,
          dt.name                                as demand_type_name,
          a.student_id,
          s.name                                 as student_name,
          a.teacher_id,
          t.name                                 as teacher_name,
          a.status,
          a.urgency,
          a.created_at,
          a.updated_at
        from attendances a
        join clients c                   on c.id  = a.client_id
        left join legal_areas la         on la.id = a.legal_area_id
        left join demand_types dt        on dt.id = a.demand_type_id
        left join profiles s             on s.id  = a.student_id
        left join profiles t             on t.id  = a.teacher_id
        where (:status_filter is null  or a.status         = :status_filter)
          and (:legal_area_id is null  or a.legal_area_id  = :legal_area_id)
          and (:demand_type_id is null or a.demand_type_id = :demand_type_id)
          and (:student_id is null     or a.student_id     = :student_id)
          and (:teacher_id is null     or a.teacher_id     = :teacher_id)
          and (:client_id is null      or a.client_id      = :client_id)
          and (cast(:urgency as boolean) is null
               or a.urgency = cast(:urgency as boolean))
          and (:from_date is null      or a.created_at    >= :from_date)
          and (:to_date is null        or a.created_at    <= :to_date)
          and (:search is null         or c.full_name ilike :search_pat)
        order by a.urgency desc, a.created_at desc
        limit :limit offset :offset
        """
    ).bindparams(
        # Tipar os parâmetros explicitamente — psycopg v3 não infere tipo
        # quando o parâmetro só aparece como NULL.
        bindparam("status_filter", type_=String),
        bindparam("legal_area_id", type_=Uuid),
        bindparam("demand_type_id", type_=Uuid),
        bindparam("student_id", type_=Uuid),
        bindparam("teacher_id", type_=Uuid),
        bindparam("client_id", type_=Uuid),
        bindparam("urgency", type_=Boolean),
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
            "status_filter": status_filter,
            "legal_area_id": legal_area_id,
            "demand_type_id": demand_type_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "client_id": client_id,
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


def get_attendance(db: Session, attendance_id: UUID) -> Attendance:
    a = (
        db.query(Attendance).filter(Attendance.id == attendance_id).one_or_none()
    )
    if a is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado.",
        )
    return a


def list_history(
    db: Session,
    attendance_id: UUID,
    current_user: Profile,
) -> list[dict[str, Any]]:
    """Lista eventos do histórico do atendimento já com o nome do usuário.

    Aplica escopo por perfil: aluno só vê histórico dos seus atendimentos,
    professor só dos casos sob sua orientação, admin vê todos.
    """
    attendance = get_attendance(db, attendance_id)
    _ensure_can_view_history(attendance, current_user)

    sql = text(
        """
        select
          h.id,
          h.attendance_id,
          h.user_id,
          p.name        as user_name,
          h.event_type,
          h.description,
          h.old_status,
          h.new_status,
          h.created_at
        from attendance_history h
        left join profiles p on p.id = h.user_id
        where h.attendance_id = :attendance_id
        order by h.created_at desc
        """
    ).bindparams(bindparam("attendance_id", type_=Uuid))
    rows = db.execute(sql, {"attendance_id": attendance_id}).mappings().all()
    return [dict(r) for r in rows]


def _ensure_can_view_history(attendance: Attendance, user: Profile) -> None:
    if user.role == ROLE_ADMIN:
        return
    if user.role == ROLE_STUDENT and attendance.student_id == user.id:
        return
    if user.role == ROLE_TEACHER and attendance.teacher_id == user.id:
        return
    raise HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Você não tem acesso ao histórico deste atendimento.",
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def create_attendance(
    db: Session, payload: AttendanceCreate, current_user: Profile
) -> Attendance:
    # student_id padrão: o próprio usuário (se for aluno).
    student_id = current_user.id if current_user.role == ROLE_STUDENT else None

    attendance = Attendance(
        client_id=payload.client_id,
        legal_area_id=payload.legal_area_id,
        demand_type_id=payload.demand_type_id,
        teacher_id=payload.teacher_id,
        student_id=student_id,
        description=payload.description,
        notes=payload.notes,
        urgency=payload.urgency,
        status="novo_atendimento",
        responsible_student_name=payload.responsible_student_name,
        responsible_student_matricula=payload.responsible_student_matricula,
    )
    db.add(attendance)
    db.flush()

    _record_history(
        db,
        attendance_id=attendance.id,
        user_id=current_user.id,
        event_type="abertura",
        description=f"Atendimento aberto por {current_user.name}.",
        old_status=None,
        new_status="novo_atendimento",
    )
    db.commit()
    db.refresh(attendance)
    return attendance


def update_attendance(
    db: Session,
    attendance_id: UUID,
    payload: AttendanceUpdate,
    current_user: Profile,
) -> Attendance:
    attendance = get_attendance(db, attendance_id)
    _ensure_can_edit(attendance, current_user)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return attendance

    for field, value in data.items():
        setattr(attendance, field, value)

    _record_history(
        db,
        attendance_id=attendance.id,
        user_id=current_user.id,
        event_type="observacao",
        description=f"Dados do atendimento atualizados por {current_user.name}.",
    )
    db.commit()
    db.refresh(attendance)
    return attendance


def change_status(
    db: Session,
    attendance_id: UUID,
    payload: AttendanceStatusUpdate,
    current_user: Profile,
) -> Attendance:
    attendance = get_attendance(db, attendance_id)
    _ensure_can_change_status(attendance, current_user, payload.status)

    if attendance.status == payload.status:
        return attendance  # noop — não gera ruído no histórico

    old_status = attendance.status
    attendance.status = payload.status

    if payload.status in FINAL_STATUSES and attendance.finished_at is None:
        attendance.finished_at = datetime.now(timezone.utc)
    if payload.status not in FINAL_STATUSES:
        attendance.finished_at = None  # reabertura

    event_type = (
        "encerramento"
        if payload.status == "finalizado"
        else "arquivamento"
        if payload.status == "arquivado"
        else "mudanca_status"
    )

    _record_history(
        db,
        attendance_id=attendance.id,
        user_id=current_user.id,
        event_type=event_type,
        description=payload.note,
        old_status=old_status,
        new_status=payload.status,
    )
    db.commit()
    db.refresh(attendance)
    return attendance


def send_to_teacher(
    db: Session,
    attendance_id: UUID,
    payload: SendToTeacherRequest,
    current_user: Profile,
) -> Attendance:
    """Atalho: muda status para `encaminhado_ao_professor` e (opcional) atribui teacher."""
    attendance = get_attendance(db, attendance_id)

    if current_user.role not in {ROLE_STUDENT, ROLE_ADMIN}:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Apenas alunos e coordenação podem encaminhar ao professor.",
        )
    if current_user.role == ROLE_STUDENT and attendance.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Atendimento finalizado — aluno não pode reencaminhar.",
        )

    if payload.teacher_id is not None:
        # valida existência e perfil
        teacher = (
            db.query(Profile)
            .filter(Profile.id == payload.teacher_id)
            .one_or_none()
        )
        if teacher is None or teacher.role != ROLE_TEACHER:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Professor inválido.",
            )
        attendance.teacher_id = payload.teacher_id

    if attendance.teacher_id is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Informe um professor antes de encaminhar.",
        )

    old_status = attendance.status
    attendance.status = "encaminhado_ao_professor"

    _record_history(
        db,
        attendance_id=attendance.id,
        user_id=current_user.id,
        event_type="encaminhamento",
        description=payload.note
        or f"Encaminhado ao professor por {current_user.name}.",
        old_status=old_status,
        new_status="encaminhado_ao_professor",
    )
    db.commit()
    db.refresh(attendance)
    return attendance
