"""Schemas Pydantic do módulo clients."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.validators import (
    is_valid_birth_date,
    is_valid_cpf,
    is_valid_phone,
    is_valid_rg,
)


MaritalStatus = Literal[
    "solteiro",
    "casado",
    "divorciado",
    "viuvo",
    "uniao_estavel",
    "separado",
]
ClientStatus = Literal["ativo", "inativo"]
DocumentStatus = Literal["pendente", "aprovado", "rejeitado", "arquivado"]
ClientHistoryEvent = Literal[
    "criacao", "atualizacao", "desativacao", "reativacao", "observacao"
]


# ---------------------------------------------------------------------------
# Mixin com validações reaproveitáveis entre Create e Update
# ---------------------------------------------------------------------------
class _ClientFieldsValidatorsMixin:
    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not is_valid_cpf(v):
            raise ValueError("CPF inválido — confira os dígitos verificadores.")
        return v

    @field_validator("rg")
    @classmethod
    def _validate_rg(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not is_valid_rg(v):
            raise ValueError("RG inválido — informe um número válido (5 a 14 caracteres).")
        return v

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not is_valid_phone(v):
            raise ValueError("Telefone inválido — informe DDD + número (10 ou 11 dígitos).")
        return v

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, v: date | None) -> date | None:
        if v is None:
            return None
        if not is_valid_birth_date(v):
            raise ValueError(
                "Data de nascimento inválida — deve estar entre 01/01/1900 e hoje."
            )
        return v

    @field_validator("state")
    @classmethod
    def _validate_state(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("UF inválida — informe as 2 letras (ex.: SP, RJ).")
        return v


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------
class ClientCreate(_ClientFieldsValidatorsMixin, BaseModel):
    full_name: str = Field(min_length=3, max_length=200)
    cpf: str = Field(
        min_length=11,
        max_length=14,
        description="Aceita com ou sem máscara — validado por dígito verificador.",
    )
    rg: str | None = Field(default=None, max_length=30)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    marital_status: MaritalStatus | None = None
    profession: str | None = Field(default=None, max_length=120)
    family_income: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    notes: str | None = Field(default=None, max_length=4000)


class ClientUpdate(_ClientFieldsValidatorsMixin, BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=200)
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    rg: str | None = Field(default=None, max_length=30)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    marital_status: MaritalStatus | None = None
    profession: str | None = Field(default=None, max_length=120)
    family_income: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    notes: str | None = Field(default=None, max_length=4000)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    cpf: str | None
    rg: str | None
    birth_date: date | None
    phone: str | None
    email: str | None
    address: str | None
    district: str | None
    city: str | None
    state: str | None
    marital_status: MaritalStatus | None
    profession: str | None
    family_income: Decimal | None
    notes: str | None
    status: ClientStatus
    created_at: datetime
    updated_at: datetime


class ClientListItem(BaseModel):
    id: UUID
    full_name: str
    cpf: str | None
    phone: str | None
    city: str | None
    status: ClientStatus
    last_attendance_at: datetime | None
    created_at: datetime


class ClientHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    user_id: UUID | None
    event_type: ClientHistoryEvent
    description: str | None
    changes: dict[str, Any] | None
    created_at: datetime


class ClientDocumentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attendance_id: UUID | None
    document_type: str
    file_name: str
    file_url: str | None
    storage_path: str
    status: DocumentStatus
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime
