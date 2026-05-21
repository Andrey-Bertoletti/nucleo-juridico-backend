"""Regras de negócio do módulo admin para taxonomias."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.admin.schemas import (
    DemandTypeCreate,
    DemandTypeUpdate,
    LegalAreaCreate,
    LegalAreaUpdate,
)
from app.modules.catalogs.models import DemandType, LegalArea


# ---------------------------------------------------------------------------
# Legal Areas
# ---------------------------------------------------------------------------
def list_legal_areas(db: Session) -> list[LegalArea]:
    return db.query(LegalArea).order_by(LegalArea.name).all()


def create_legal_area(db: Session, payload: LegalAreaCreate) -> LegalArea:
    name = payload.name.strip()
    if db.query(LegalArea).filter(LegalArea.name == name).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma área jurídica com este nome.",
        )
    area = LegalArea(name=name, status=payload.status)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def update_legal_area(
    db: Session, area_id: UUID, payload: LegalAreaUpdate
) -> LegalArea:
    area = db.query(LegalArea).filter(LegalArea.id == area_id).one_or_none()
    if area is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Área jurídica não encontrada.",
        )

    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")
    if new_name is not None:
        new_name = new_name.strip()
        if (
            new_name != area.name
            and db.query(LegalArea)
            .filter(LegalArea.name == new_name)
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma área jurídica com este nome.",
            )
        area.name = new_name
    if "status" in data and data["status"] is not None:
        area.status = data["status"]

    db.commit()
    db.refresh(area)
    return area


# ---------------------------------------------------------------------------
# Demand Types
# ---------------------------------------------------------------------------
def list_demand_types(
    db: Session, *, legal_area_id: UUID | None = None
) -> list[DemandType]:
    q = db.query(DemandType)
    if legal_area_id is not None:
        q = q.filter(DemandType.legal_area_id == legal_area_id)
    return q.order_by(DemandType.name).all()


def _ensure_area_exists(db: Session, area_id: UUID) -> None:
    if not db.query(LegalArea).filter(LegalArea.id == area_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Área jurídica informada não existe.",
        )


def create_demand_type(db: Session, payload: DemandTypeCreate) -> DemandType:
    _ensure_area_exists(db, payload.legal_area_id)
    name = payload.name.strip()
    if (
        db.query(DemandType)
        .filter(
            DemandType.legal_area_id == payload.legal_area_id,
            DemandType.name == name,
        )
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um tipo de demanda com este nome na área selecionada.",
        )
    dt = DemandType(
        legal_area_id=payload.legal_area_id,
        name=name,
        status=payload.status,
    )
    db.add(dt)
    db.commit()
    db.refresh(dt)
    return dt


def update_demand_type(
    db: Session, demand_type_id: UUID, payload: DemandTypeUpdate
) -> DemandType:
    dt = (
        db.query(DemandType)
        .filter(DemandType.id == demand_type_id)
        .one_or_none()
    )
    if dt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de demanda não encontrado.",
        )

    data = payload.model_dump(exclude_unset=True)
    new_area_id = data.get("legal_area_id")
    if new_area_id is not None and new_area_id != dt.legal_area_id:
        _ensure_area_exists(db, new_area_id)
        dt.legal_area_id = new_area_id

    new_name = data.get("name")
    target_area = new_area_id or dt.legal_area_id
    target_name = new_name.strip() if new_name is not None else dt.name
    if (new_name is not None or new_area_id is not None) and (
        db.query(DemandType)
        .filter(
            DemandType.legal_area_id == target_area,
            DemandType.name == target_name,
            DemandType.id != dt.id,
        )
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um tipo de demanda com este nome na área selecionada.",
        )
    if new_name is not None:
        dt.name = target_name
    if "status" in data and data["status"] is not None:
        dt.status = data["status"]

    db.commit()
    db.refresh(dt)
    return dt
