"""Dependências de injeção compartilhadas pelas rotas."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_supabase_jwt
from app.database.session import get_db
from app.modules.users.models import Profile
from app.services.supabase_client import get_admin_client


logger = logging.getLogger("nucleo_juridico")


# --- Papéis ---------------------------------------------------------------
ROLE_ADMIN = "admin_coordenacao"
ROLE_TEACHER = "professor_orientador"
ROLE_STUDENT = "aluno_estagiario"
ALL_ROLES = {ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT}


bearer_scheme = HTTPBearer(auto_error=True, description="Token JWT do Supabase Auth.")

DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


def _jwt_is_oauth(payload: dict) -> bool:
    """True quando o JWT veio de um provider externo (Google etc.), não 'email'."""
    app_meta = payload.get("app_metadata") or {}
    provider = app_meta.get("provider")
    providers = app_meta.get("providers") or []
    if provider and provider != "email":
        return True
    return any(p != "email" for p in providers)


def _purge_orphan_oauth_user(auth_user_id: str) -> None:
    """Remove o auth.users criado pelo Supabase no signup OAuth sem profile.

    Sem esse cleanup, o Supabase fica com um registro órfão a cada tentativa de
    login com Google de alguém que não foi cadastrado pela coordenação.
    Best-effort: falha aqui não muda a resposta 404 ao cliente.
    """
    try:
        get_admin_client().auth.admin.delete_user(auth_user_id)
        logger.info(
            "auth.users órfão removido após login OAuth sem profile (id=%s).",
            auth_user_id,
        )
    except Exception:  # noqa: BLE001 — cleanup é best-effort
        logger.exception(
            "Falha ao remover auth.users órfão (id=%s) — registro pode ter ficado preso.",
            auth_user_id,
        )


def get_current_user(credentials: BearerCredentials, db: DbSession) -> Profile:
    """Decodifica o JWT, carrega o profile e bloqueia usuários não-ativos."""
    payload = decode_supabase_jwt(credentials.credentials)

    raw_user_id = payload.get("sub")
    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário.",
        )

    try:
        auth_user_id = UUID(raw_user_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuário inválido no token.",
        ) from exc

    profile = (
        db.query(Profile).filter(Profile.user_id == auth_user_id).one_or_none()
    )
    if profile is None:
        # Signup via OAuth (Google) cria um auth.users automaticamente — se
        # não há profile, o usuário não foi cadastrado pela coordenação.
        # Apaga o auth.users para não acumular órfãos, e devolve mensagem
        # clara dizendo para procurar a coordenação.
        if _jwt_is_oauth(payload):
            _purge_orphan_oauth_user(str(auth_user_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Você ainda não foi cadastrado no sistema. "
                "Entre em contato com a coordenação do NPJ para solicitar acesso."
            ),
        )
    if profile.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: usuário inativo ou bloqueado.",
        )
    return profile


CurrentUser = Annotated[Profile, Depends(get_current_user)]


def _require_roles(*allowed: str):
    """Fábrica de dependência que exige um dos papéis informados."""

    def checker(current_user: CurrentUser) -> Profile:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: permissão insuficiente.",
            )
        return current_user

    return checker


# Admin é estrito; teacher/student incluem admin (admin transita por tudo).
require_admin = _require_roles(ROLE_ADMIN)
require_teacher = _require_roles(ROLE_TEACHER, ROLE_ADMIN)
require_student = _require_roles(ROLE_STUDENT, ROLE_ADMIN)
