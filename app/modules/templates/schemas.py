"""Schemas Pydantic do módulo templates."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


TemplateType = Literal["relatorio", "atendimento", "documento"]
TemplateStatus = Literal["ativo", "inativo"]
DynamicFieldType = Literal["text", "textarea", "number", "date", "select"]


class DynamicField(BaseModel):
    """Definição de um campo a ser preenchido na geração do documento."""

    name: str = Field(..., min_length=1, max_length=60, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    label: str = Field(..., min_length=1, max_length=120)
    type: DynamicFieldType = "text"
    required: bool = True
    # Para `type=select`: lista de opções; ignorado nos outros casos.
    options: list[str] | None = None


class TemplateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    type: TemplateType
    content: str = Field(..., min_length=1)
    dynamic_fields: list[DynamicField] = Field(default_factory=list)
    status: TemplateStatus = "ativo"


class TemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    type: TemplateType | None = None
    content: str | None = Field(default=None, min_length=1)
    dynamic_fields: list[DynamicField] | None = None
    status: TemplateStatus | None = None


class TemplateStatusUpdate(BaseModel):
    status: TemplateStatus


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    type: TemplateType
    content: str
    dynamic_fields: list[dict[str, Any]]
    status: TemplateStatus
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Generated Documents
# ---------------------------------------------------------------------------
class GenerateDocumentRequest(BaseModel):
    """Payload de geração — dados preenchidos + identificação obrigatória do
    aluno responsável (porque o login de aluno é compartilhado)."""

    # Identificação manual do aluno (NÃO derivar do user logado).
    student_name: str = Field(..., min_length=2, max_length=200)
    student_matricula: str = Field(..., min_length=1, max_length=50)
    attendance_date: date
    # Chave = nome do campo dinâmico do template; valor = string já formatada
    # pelo frontend. O service valida que todos os `required` foram preenchidos.
    filled_data: dict[str, Any] = Field(default_factory=dict)
    # Vínculos opcionais com registros do sistema.
    attendance_id: UUID | None = None
    client_id: UUID | None = None

    @field_validator("student_name", "student_matricula")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class GeneratedDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    template_type: TemplateType
    template_title: str
    generated_by_user_id: UUID | None
    student_name: str
    student_matricula: str
    attendance_date: date
    filled_data: dict[str, Any]
    final_content: str
    attendance_id: UUID | None
    client_id: UUID | None
    generated_at: datetime
