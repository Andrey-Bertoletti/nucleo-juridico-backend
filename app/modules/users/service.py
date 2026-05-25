"""Regras de negócio do módulo users."""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.users.models import Profile
from app.modules.users.schemas import UserCreate, UserStatusUpdate, UserUpdate
from app.services.supabase_client import get_admin_client


logger = logging.getLogger("nucleo_juridico")


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


def _delete_supabase_auth_user(auth_user_id: str) -> None:
    """Tenta excluir um usuário no Supabase Auth (best-effort, não levanta).

    Usado como rollback compensatório quando a persistência do `profile`
    falha após a criação da conta no Supabase Auth — evita deixar usuário
    órfão (auth.users sem profile correspondente).
    """
    try:
        admin = get_admin_client()
        admin.auth.admin.delete_user(auth_user_id)
    except Exception:  # noqa: BLE001 — rollback é best-effort
        logger.exception(
            "Falha no rollback do auth.users (id=%s) — usuário pode ter ficado órfão.",
            auth_user_id,
        )


def create_user(db: Session, payload: UserCreate) -> Profile:
    """Cria a conta no Supabase Auth e o profile correspondente.

    Em caso de falha após a criação no Supabase Auth (e-mail duplicado em
    profiles, erro de banco, retorno inválido do Supabase), a conta criada
    no Supabase Auth é removida em rollback compensatório — evita órfão.
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
    except Exception as exc:  # noqa: BLE001 — supabase pode lançar várias subclasses
        # Log detalhado fica no servidor; resposta é genérica para não vazar
        # estrutura interna do Supabase Auth.
        logger.exception("Falha ao criar usuário no Supabase Auth.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível criar o usuário no provedor de autenticação.",
        ) from exc

    auth_user = getattr(result, "user", None)
    auth_user_id = getattr(auth_user, "id", None) if auth_user is not None else None
    if auth_user is None or auth_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase não retornou um usuário válido.",
        )

    auth_user_id_str = str(auth_user_id)

    # A partir daqui qualquer falha exige rollback compensatório no auth.users.
    try:
        profile = Profile(
            user_id=UUID(auth_user_id_str),
            name=payload.name,
            email=payload.email,
            role=payload.role,
            status="ativo",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        db.rollback()
        _delete_supabase_auth_user(auth_user_id_str)
        logger.exception("Falha ao persistir profile após criar auth.users.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível concluir o cadastro do usuário.",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — qualquer outro erro também limpa o auth.users
        db.rollback()
        _delete_supabase_auth_user(auth_user_id_str)
        logger.exception("Erro inesperado ao criar profile.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível concluir o cadastro do usuário.",
        ) from exc


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
