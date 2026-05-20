"""Regras de negócio do módulo triage."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import ROLE_ADMIN, ROLE_STUDENT
from app.modules.attendances.models import Attendance, AttendanceHistory
from app.modules.triage.models import Triage
from app.modules.triage.schemas import TriageCreate, TriageUpdate
from app.modules.users.models import Profile


FINAL_ATTENDANCE_STATUSES = {"finalizado", "arquivado"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_attendance(db: Session, attendance_id: UUID) -> Attendance:
    a = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .one_or_none()
    )
    if a is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado.",
        )
    return a


def _ensure_can_edit(attendance: Attendance, user: Profile) -> None:
    if user.role not in {ROLE_STUDENT, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas alunos/estagiários e coordenação podem editar a triagem.",
        )
    if attendance.status in FINAL_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Atendimento finalizado — triagem não pode ser editada.",
        )


def _record_history(
    db: Session,
    *,
    attendance_id: UUID,
    user_id: UUID | None,
    description: str,
) -> None:
    db.add(
        AttendanceHistory(
            attendance_id=attendance_id,
            user_id=user_id,
            event_type="triagem",
            description=description,
        )
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def get_triage(db: Session, attendance_id: UUID) -> Triage:
    _get_attendance(db, attendance_id)
    t = (
        db.query(Triage)
        .filter(Triage.attendance_id == attendance_id)
        .one_or_none()
    )
    if t is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triagem ainda não preenchida.",
        )
    return t


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def create_triage(
    db: Session,
    attendance_id: UUID,
    payload: TriageCreate,
    current_user: Profile,
) -> Triage:
    attendance = _get_attendance(db, attendance_id)
    _ensure_can_edit(attendance, current_user)

    existing = (
        db.query(Triage)
        .filter(Triage.attendance_id == attendance_id)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe triagem para este atendimento — use PATCH para atualizar.",
        )

    triage = Triage(
        attendance_id=attendance_id,
        client_report=payload.client_report,
        has_urgent_deadline=payload.has_urgent_deadline,
        urgency_description=payload.urgency_description,
        presented_documents=payload.presented_documents,
        pending_documents=payload.pending_documents,
        suggested_forwarding=payload.suggested_forwarding,
        student_notes=payload.student_notes,
    )
    db.add(triage)

    # Promove o atendimento para `em_triagem` (se ainda for novo).
    if attendance.status == "novo_atendimento":
        attendance.status = "em_triagem"

    # Reflete a urgência também no campo do atendimento.
    if payload.has_urgent_deadline:
        attendance.urgency = True

    _record_history(
        db,
        attendance_id=attendance_id,
        user_id=current_user.id,
        description=f"Triagem preenchida por {current_user.name}.",
    )

    db.commit()
    db.refresh(triage)
    return triage


def update_triage(
    db: Session,
    attendance_id: UUID,
    payload: TriageUpdate,
    current_user: Profile,
) -> Triage:
    attendance = _get_attendance(db, attendance_id)
    _ensure_can_edit(attendance, current_user)

    triage = (
        db.query(Triage)
        .filter(Triage.attendance_id == attendance_id)
        .one_or_none()
    )
    if triage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triagem ainda não criada — use POST primeiro.",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return triage

    for field, value in data.items():
        setattr(triage, field, value)

    # Validação pós-merge: client_report não pode ficar vazio,
    # urgência exige descrição.
    if triage.client_report is None or not triage.client_report.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O relato do cliente (client_report) é obrigatório.",
        )
    if triage.has_urgent_deadline and (
        triage.urgency_description is None
        or not triage.urgency_description.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Descreva a urgência quando há prazo urgente.",
        )

    if triage.has_urgent_deadline:
        attendance.urgency = True

    _record_history(
        db,
        attendance_id=attendance_id,
        user_id=current_user.id,
        description=f"Triagem atualizada por {current_user.name}.",
    )

    db.commit()
    db.refresh(triage)
    return triage
