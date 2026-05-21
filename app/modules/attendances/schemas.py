"""Schemas Pydantic do módulo attendances."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AttendanceStatus = Literal[
    "novo_atendimento",
    "em_triagem",
    "aguardando_documentos",
    "encaminhado_ao_professor",
    "em_analise_pelo_professor",
    "correcao_solicitada",
    "aguardando_retorno_cliente",
    "encaminhamento_aprovado",
    "finalizado",
    "arquivado",
]


HistoryEventType = Literal[
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
]


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
class AttendanceCreate(BaseModel):
    client_id: UUID
    legal_area_id: UUID | None = None
    demand_type_id: UUID | None = None
    teacher_id: UUID | None = None
    description: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)
    urgency: bool = False


class AttendanceUpdate(BaseModel):
    legal_area_id: UUID | None = None
    demand_type_id: UUID | None = None
    teacher_id: UUID | None = None
    student_id: UUID | None = None
    description: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)
    urgency: bool | None = None


class AttendanceStatusUpdate(BaseModel):
    status: AttendanceStatus
    note: str | None = Field(default=None, max_length=2000)


class SendToTeacherRequest(BaseModel):
    teacher_id: UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Respostas
# ---------------------------------------------------------------------------
class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    legal_area_id: UUID | None
    demand_type_id: UUID | None
    student_id: UUID | None
    teacher_id: UUID | None
    description: str | None
    notes: str | None
    urgency: bool
    status: AttendanceStatus
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


class AttendanceListItem(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    legal_area_id: UUID | None
    legal_area_name: str | None
    demand_type_id: UUID | None
    demand_type_name: str | None
    student_id: UUID | None
    student_name: str | None
    teacher_id: UUID | None
    teacher_name: str | None
    status: AttendanceStatus
    urgency: bool
    created_at: datetime
    updated_at: datetime


class AttendanceHistoryItem(BaseModel):
    id: UUID
    attendance_id: UUID
    user_id: UUID | None
    user_name: str | None
    event_type: HistoryEventType
    description: str | None
    old_status: AttendanceStatus | None
    new_status: AttendanceStatus | None
    created_at: datetime
