"""Schemas dos catálogos."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


CatalogStatus = Literal["ativo", "inativo"]


class LegalAreaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: CatalogStatus
    created_at: datetime
    updated_at: datetime


class DemandTypeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_area_id: UUID
    name: str
    status: CatalogStatus
    created_at: datetime
    updated_at: datetime


class UserOption(BaseModel):
    """Versão enxuta de Profile para selects e filtros."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
