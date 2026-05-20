"""Rotas do módulo users."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    ROLE_ADMIN,
    CurrentUser,
    DbSession,
    require_admin,
)
from app.modules.users.models import Profile
from app.modules.users import service
from app.modules.users.schemas import (
    UserCreate,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    db: DbSession,
    _: Profile = Depends(require_admin),
) -> list[UserResponse]:
    return service.list_users(db)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbSession,
    _: Profile = Depends(require_admin),
) -> UserResponse:
    return service.create_user(db, payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    """Admin lê qualquer usuário; demais perfis somente o próprio."""
    profile = service.get_user(db, user_id)
    if current_user.role != ROLE_ADMIN and current_user.id != profile.id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: você só pode visualizar o próprio usuário.",
        )
    return profile


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    """Admin atualiza qualquer usuário; demais perfis somente o próprio (sem alterar role)."""
    target = service.get_user(db, user_id)
    is_admin = current_user.role == ROLE_ADMIN
    is_self = current_user.id == target.id

    if not is_admin and not is_self:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: você só pode editar o próprio usuário.",
        )

    return service.update_user(
        db, user_id, payload, allow_role_change=is_admin
    )


@router.patch("/{user_id}/status", response_model=UserResponse)
def change_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    db: DbSession,
    _: Profile = Depends(require_admin),
) -> UserResponse:
    return service.change_status(db, user_id, payload)
