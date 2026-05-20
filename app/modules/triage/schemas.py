"""Schemas Pydantic do módulo triage."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TriageBase(BaseModel):
    client_report: str | None = Field(default=None, max_length=8000)
    has_urgent_deadline: bool = False
    urgency_description: str | None = Field(default=None, max_length=2000)
    presented_documents: str | None = Field(default=None, max_length=4000)
    pending_documents: str | None = Field(default=None, max_length=4000)
    suggested_forwarding: str | None = Field(default=None, max_length=2000)
    student_notes: str | None = Field(default=None, max_length=4000)


class TriageCreate(TriageBase):
    """Criação da triagem.

    Regras:
      - `client_report` é obrigatório (string não-vazia).
      - Se `has_urgent_deadline` for true, `urgency_description` é obrigatório.
    """

    @model_validator(mode="after")
    def _validate_required_fields(self) -> "TriageCreate":
        if self.client_report is None or not self.client_report.strip():
            raise ValueError("O relato do cliente (client_report) é obrigatório.")
        if self.has_urgent_deadline and (
            self.urgency_description is None
            or not self.urgency_description.strip()
        ):
            raise ValueError(
                "Descreva a urgência (urgency_description) quando há prazo urgente."
            )
        return self


class TriageUpdate(TriageBase):
    """Atualização parcial — todos os campos são opcionais.

    A validação condicional (urgência exige descrição) é aplicada considerando
    o estado MERGED no service (current DB + payload).
    """


class TriageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attendance_id: UUID
    client_report: str | None
    has_urgent_deadline: bool
    urgency_description: str | None
    presented_documents: str | None
    pending_documents: str | None
    suggested_forwarding: str | None
    student_notes: str | None
    created_at: datetime
    updated_at: datetime
