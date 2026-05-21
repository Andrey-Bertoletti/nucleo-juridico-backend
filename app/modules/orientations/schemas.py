"""Schemas Pydantic do módulo orientations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


OrientationDecision = Literal[
    "solicitar_correcao",
    "solicitar_documentos",
    "aprovar_encaminhamento",
    "finalizar_atendimento",
]


class OrientationCreate(BaseModel):
    orientation_text: str = Field(min_length=1, max_length=8000)
    teacher_notes: str | None = Field(default=None, max_length=4000)
    decision: OrientationDecision | None = None


class OrientationUpdate(BaseModel):
    """PATCH só permite editar texto/observação — a decisão é imutável.

    Para mudar de decisão, registre uma NOVA orientação.
    """

    orientation_text: str | None = Field(default=None, min_length=1, max_length=8000)
    teacher_notes: str | None = Field(default=None, max_length=4000)


class OrientationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attendance_id: UUID
    teacher_id: UUID | None
    orientation_text: str
    teacher_notes: str | None
    decision: OrientationDecision | None
    created_at: datetime
    updated_at: datetime


class TeacherCaseItem(BaseModel):
    """Linha enxuta da fila de casos do professor."""

    id: UUID
    client_id: UUID
    client_name: str
    legal_area_id: UUID | None
    legal_area_name: str | None
    student_id: UUID | None
    student_name: str | None
    status: str
    urgency: bool
    created_at: datetime
    updated_at: datetime
