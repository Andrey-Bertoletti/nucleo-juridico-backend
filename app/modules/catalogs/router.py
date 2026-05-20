"""Endpoints de catálogo — taxonomias e listas auxiliares para selects."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import (
    ROLE_STUDENT,
    ROLE_TEACHER,
    CurrentUser,
    DbSession,
)
from app.modules.catalogs.models import DemandType, LegalArea
from app.modules.catalogs.schemas import (
    DemandTypeItem,
    LegalAreaItem,
    UserOption,
)
from app.modules.users.models import Profile


router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@router.get("/legal-areas", response_model=list[LegalAreaItem])
def list_legal_areas(
    db: DbSession,
    _current: CurrentUser,
    only_active: bool = Query(default=True),
) -> list[LegalAreaItem]:
    q = db.query(LegalArea)
    if only_active:
        q = q.filter(LegalArea.status == "ativo")
    return q.order_by(LegalArea.name).all()  # type: ignore[return-value]


@router.get("/demand-types", response_model=list[DemandTypeItem])
def list_demand_types(
    db: DbSession,
    _current: CurrentUser,
    legal_area_id: UUID | None = Query(default=None),
    only_active: bool = Query(default=True),
) -> list[DemandTypeItem]:
    q = db.query(DemandType)
    if legal_area_id is not None:
        q = q.filter(DemandType.legal_area_id == legal_area_id)
    if only_active:
        q = q.filter(DemandType.status == "ativo")
    return q.order_by(DemandType.name).all()  # type: ignore[return-value]


@router.get("/teachers", response_model=list[UserOption])
def list_teachers(db: DbSession, _current: CurrentUser) -> list[UserOption]:
    return (
        db.query(Profile)
        .filter(Profile.role == ROLE_TEACHER, Profile.status == "ativo")
        .order_by(Profile.name)
        .all()
    )  # type: ignore[return-value]


@router.get("/students", response_model=list[UserOption])
def list_students(db: DbSession, _current: CurrentUser) -> list[UserOption]:
    return (
        db.query(Profile)
        .filter(Profile.role == ROLE_STUDENT, Profile.status == "ativo")
        .order_by(Profile.name)
        .all()
    )  # type: ignore[return-value]
