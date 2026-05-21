"""Rotas do módulo admin — todas exigem `admin_coordenacao`."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentUser, DbSession, require_admin
from app.modules.admin import service
from app.modules.admin.schemas import (
    DemandTypeCreate,
    DemandTypeUpdate,
    LegalAreaCreate,
    LegalAreaUpdate,
)
from app.modules.catalogs.schemas import DemandTypeItem, LegalAreaItem
from app.modules.users import service as users_service
from app.modules.users.models import Profile
from app.modules.users.schemas import (
    UserCreate,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    # Todas as rotas do admin exigem perfil admin_coordenacao
    dependencies=[Depends(require_admin)],
)


# ===========================================================================
# Usuários
# ===========================================================================
@router.get("/users", response_model=list[UserResponse])
def list_users(db: DbSession, _current: CurrentUser) -> list[UserResponse]:
    return users_service.list_users(db)  # type: ignore[return-value]


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate, db: DbSession, _current: CurrentUser
) -> UserResponse:
    return users_service.create_user(db, payload)  # type: ignore[return-value]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID, db: DbSession, _current: CurrentUser
) -> UserResponse:
    return users_service.get_user(db, user_id)  # type: ignore[return-value]


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    _current: CurrentUser,
) -> UserResponse:
    return users_service.update_user(
        db, user_id, payload, allow_role_change=True
    )  # type: ignore[return-value]


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def change_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    db: DbSession,
    _current: CurrentUser,
) -> UserResponse:
    return users_service.change_status(db, user_id, payload)  # type: ignore[return-value]


# ===========================================================================
# Áreas jurídicas
# ===========================================================================
@router.get("/legal-areas", response_model=list[LegalAreaItem])
def list_legal_areas(
    db: DbSession, _current: CurrentUser
) -> list[LegalAreaItem]:
    return service.list_legal_areas(db)  # type: ignore[return-value]


@router.post(
    "/legal-areas",
    response_model=LegalAreaItem,
    status_code=status.HTTP_201_CREATED,
)
def create_legal_area(
    payload: LegalAreaCreate, db: DbSession, _current: CurrentUser
) -> LegalAreaItem:
    return service.create_legal_area(db, payload)  # type: ignore[return-value]


@router.patch("/legal-areas/{area_id}", response_model=LegalAreaItem)
def update_legal_area(
    area_id: UUID,
    payload: LegalAreaUpdate,
    db: DbSession,
    _current: CurrentUser,
) -> LegalAreaItem:
    return service.update_legal_area(db, area_id, payload)  # type: ignore[return-value]


# ===========================================================================
# Tipos de demanda
# ===========================================================================
@router.get("/demand-types", response_model=list[DemandTypeItem])
def list_demand_types(
    db: DbSession,
    _current: CurrentUser,
    legal_area_id: UUID | None = Query(default=None),
) -> list[DemandTypeItem]:
    return service.list_demand_types(db, legal_area_id=legal_area_id)  # type: ignore[return-value]


@router.post(
    "/demand-types",
    response_model=DemandTypeItem,
    status_code=status.HTTP_201_CREATED,
)
def create_demand_type(
    payload: DemandTypeCreate, db: DbSession, _current: CurrentUser
) -> DemandTypeItem:
    return service.create_demand_type(db, payload)  # type: ignore[return-value]


@router.patch(
    "/demand-types/{demand_type_id}", response_model=DemandTypeItem
)
def update_demand_type(
    demand_type_id: UUID,
    payload: DemandTypeUpdate,
    db: DbSession,
    _current: CurrentUser,
) -> DemandTypeItem:
    return service.update_demand_type(db, demand_type_id, payload)  # type: ignore[return-value]


# Aliasing dependency import explícito (evita unused import warning)
_ = Profile  # noqa: F841
