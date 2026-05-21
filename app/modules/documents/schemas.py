"""Schemas Pydantic do módulo documents."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


DocumentType = Literal[
    "rg",
    "cpf",
    "comprovante_residencia",
    "comprovante_renda",
    "certidao",
    "documento_caso",
    "outros",
]
DocumentStatus = Literal["entregue", "pendente", "removido"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID | None
    attendance_id: UUID | None
    document_type: DocumentType
    file_name: str
    file_url: str | None
    storage_path: str
    status: DocumentStatus
    notes: str | None
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus
