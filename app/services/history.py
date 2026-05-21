"""Serviço reutilizável para registrar eventos no histórico de um atendimento.

Use este helper em qualquer módulo que altere algo relevante ao caso jurídico.
Ele apenas adiciona a entrada à `Session` — o `commit` deve ser feito pelo
chamador, junto da operação principal (mesma transação).

Exemplo:

    from app.services.history import create_attendance_history_event

    create_attendance_history_event(
        db,
        attendance_id=att.id,
        user_id=current_user.id,
        event_type="mudanca_status",
        description="Aluno enviou ao professor para análise.",
        old_status="em_triagem",
        new_status="encaminhado_ao_professor",
    )
    db.commit()
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.attendances.models import AttendanceHistory


# Mantém em sincronia com o check constraint da migração.
VALID_EVENT_TYPES: set[str] = {
    "abertura",
    "triagem",
    "orientacao",
    "encaminhamento",
    "documento_adicionado",
    "documento_aprovado",
    "documento_rejeitado",
    "agendamento",
    "retorno",
    "mudanca_status",
    "observacao",
    "encerramento",
    "arquivamento",
}


def create_attendance_history_event(
    db: Session,
    *,
    attendance_id: UUID,
    user_id: UUID | None,
    event_type: str,
    description: str | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
) -> AttendanceHistory:
    """Adiciona um evento ao histórico do atendimento (sem commitar)."""
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"event_type '{event_type}' não é permitido pelo check constraint."
        )
    entry = AttendanceHistory(
        attendance_id=attendance_id,
        user_id=user_id,
        event_type=event_type,
        description=description,
        old_status=old_status,
        new_status=new_status,
    )
    db.add(entry)
    return entry
