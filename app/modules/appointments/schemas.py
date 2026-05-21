"""Schemas Pydantic do módulo appointments."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AppointmentStatus = Literal[
    "agendado",
    "confirmado",
    "compareceu",
    "nao_compareceu",
    "remarcado",
    "cancelado",
]


class AppointmentCreate(BaseModel):
    client_id: UUID
    attendance_id: UUID | None = None
    responsible_id: UUID | None = Field(
        default=None,
        description="Se omitido, o usuário autenticado vira o responsável.",
    )
    appointment_date: date
    appointment_time: time | None = None
    reason: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentUpdate(BaseModel):
    attendance_id: UUID | None = None
    responsible_id: UUID | None = None
    appointment_date: date | None = None
    appointment_time: time | None = None
    reason: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    note: str | None = Field(default=None, max_length=2000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    attendance_id: UUID | None
    responsible_id: UUID | None
    appointment_date: date
    appointment_time: time | None
    reason: str | None
    status: AppointmentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AppointmentListItem(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    attendance_id: UUID | None
    responsible_id: UUID | None
    responsible_name: str | None
    appointment_date: date
    appointment_time: time | None
    reason: str | None
    status: AppointmentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
