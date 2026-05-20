"""Regras de negócio do módulo users."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.users.models import Profile
from app.modules.users.schemas import UserCreate, UserStatusUpdate, UserUpdate
from app.services.supabase_client import get_admin_client


def list_users(db: Session) -> list[Profile]:
    return (
        db.query(Profile).order_by(Profile.created_at.desc()).all()
    )


def get_user(db: Session, user_id: UUID) -> Profile:
    profile = db.query(Profile).filter(Profile.id == user_id).one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )
    return profile


def create_user(db: Session, payload: UserCreate) -> Profile:
    """Cria a conta no Supabase Auth e o profile correspondente.

    O `user_id` do profile **deve** apontar para `auth.users.id`. Se a criação
    do profile falhar, rolling back manual ainda não está implementado — o
    usuário ficaria no Supabase Auth órfão; revisitar antes de produção.
    """
    if db.query(Profile).filter(Profile.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este e-mail.",
        )

    admin = get_admin_client()
    try:
        result = admin.auth.admin.create_user(
            {
                "email": payload.email,
                "password": payload.password,
                "email_confirm": True,
                "user_metadata": {"name": payload.name, "role": payload.role},
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha ao criar usuário no Supabase Auth: {exc}",
        ) from exc

    auth_user = getattr(result, "user", None)
    if auth_user is None or getattr(auth_user, "id", None) is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase não retornou um usuário válido.",
        )

    profile = Profile(
        user_id=UUID(str(auth_user.id)),
        name=payload.name,
        email=payload.email,
        role=payload.role,
        status="ativo",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_user(
    db: Session,
    user_id: UUID,
    payload: UserUpdate,
    *,
    allow_role_change: bool,
) -> Profile:
    profile = get_user(db, user_id)

    if payload.role is not None and not allow_role_change:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem alterar o papel do usuário.",
        )

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != profile.email:
        if db.query(Profile).filter(Profile.email == data["email"]).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um usuário com este e-mail.",
            )

    for field, value in data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


def change_status(
    db: Session, user_id: UUID, payload: UserStatusUpdate
) -> Profile:
    profile = get_user(db, user_id)
    profile.status = payload.status
    db.commit()
    db.refresh(profile)
    return profile
