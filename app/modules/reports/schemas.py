"""Schemas Pydantic do módulo reports."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.modules.attendances.schemas import AttendanceListItem


Role = Literal["aluno_estagiario", "professor_orientador", "admin_coordenacao"]


class StatusCount(BaseModel):
    status: str
    label: str
    count: int


class AreaCount(BaseModel):
    legal_area_id: UUID | None
    legal_area_name: str | None
    count: int


class ProductivityRow(BaseModel):
    user_id: UUID
    user_name: str
    total: int
    em_andamento: int
    finalizados: int
    urgentes: int


class DashboardCounters(BaseModel):
    novo_atendimento: int = 0
    em_triagem: int = 0
    aguardando_documentos: int = 0
    encaminhado_ao_professor: int = 0
    em_analise_pelo_professor: int = 0
    correcao_solicitada: int = 0
    aguardando_retorno_cliente: int = 0
    encaminhamento_aprovado: int = 0
    finalizado: int = 0
    arquivado: int = 0


class DashboardResponse(BaseModel):
    role: Role
    period_from: date | None
    period_to: date | None
    total: int
    counters: DashboardCounters
    urgentes: int
    appointments_today: int
    pending_documents: int
    pending_teacher_analysis: int


class ReportsSummary(BaseModel):
    role: Role
    period_from: date | None
    period_to: date | None
    total: int
    counters: DashboardCounters
    urgentes: int


class PendingItemsResponse(BaseModel):
    items: list[AttendanceListItem]
    total: int
