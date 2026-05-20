"""Dependências de injeção compartilhadas pelas rotas."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_supabase_jwt
from app.database.session import get_db
from app.modules.users.models import Profile


# --- Papéis ---------------------------------------------------------------
ROLE_ADMIN = "admin_coordenacao"
ROLE_TEACHER = "professor_orientador"
ROLE_STUDENT = "aluno_estagiario"
ALL_ROLES = {ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT}


bearer_scheme = HTTPBearer(auto_error=True, description="Token JWT do Supabase Auth.")

DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de usuário não encontrado.",
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
