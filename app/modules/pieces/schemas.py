"""Schemas Pydantic do módulo pieces."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


PieceStatus = Literal[
    "entregue",
    "em_correcao",
    "corrigida",
    "devolvida_para_ajuste",
]


# ---------------------------------------------------------------------------
# Respostas
# ---------------------------------------------------------------------------
class PieceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID | None
    student_name: str | None = None
    attendance_id: UUID | None
    title: str
    description: str | None
    file_name: str
    file_url: str | None = None
    storage_path: str
    status: PieceStatus
    corrected_by: UUID | None
    corrected_by_name: str | None = None
    correction_notes: str | None
    student_notes: str | None
    delivered_at: datetime
    corrected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PieceListItem(BaseModel):
    id: UUID
    student_id: UUID | None
    student_name: str | None
    attendance_id: UUID | None
    title: str
    file_name: str
    status: PieceStatus
    delivered_at: datetime
    corrected_at: datetime | None
    corrected_by_name: str | None


class PieceStudentSummary(BaseModel):
    student_id: UUID
    student_name: str
    total: int = 0
    entregue: int = 0
    em_correcao: int = 0
    corrigida: int = 0
    devolvida_para_ajuste: int = 0


class PieceStats(BaseModel):
    total: int = 0
    entregue: int = 0
    em_correcao: int = 0
    corrigida: int = 0
    devolvida_para_ajuste: int = 0


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
class PieceUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    student_notes: str | None = Field(default=None, max_length=4000)


class PieceCorrection(BaseModel):
    status: Literal["em_correcao", "corrigida", "devolvida_para_ajuste"]
    correction_notes: str | None = Field(default=None, max_length=4000)


class PieceDownloadResponse(BaseModel):
    file_name: str
    signed_url: str
