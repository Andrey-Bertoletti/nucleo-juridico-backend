"""Schemas Pydantic do módulo admin (taxonomias)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


CatalogStatus = Literal["ativo", "inativo"]


# ---------------------------------------------------------------------------
# Legal Areas
# ---------------------------------------------------------------------------
class LegalAreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    status: CatalogStatus = "ativo"


class LegalAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: CatalogStatus | None = None


# ---------------------------------------------------------------------------
# Demand Types
# ---------------------------------------------------------------------------
class DemandTypeCreate(BaseModel):
    legal_area_id: UUID
    name: str = Field(min_length=2, max_length=200)
    status: CatalogStatus = "ativo"


class DemandTypeUpdate(BaseModel):
    legal_area_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: CatalogStatus | None = None
