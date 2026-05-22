"""Regras de negócio do módulo auth — orquestra o Supabase Auth.

O **cadastro de usuários** acontece via `POST /admin/users` (módulo admin),
que requer perfil `admin_coordenacao`. Não há cadastro público — o sistema
gerencia dados jurídicos sigilosos.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.users.models import Profile
from app.services.supabase_client import get_admin_client, get_anon_client


def login(db: Session, email: str, password: str) -> tuple[dict, Profile]:
    """Autentica via Supabase e retorna tokens + profile carregado do banco."""
    client = get_anon_client()
    try:
        result = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:  # noqa: BLE001 — supabase pode lançar várias subclasses
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        ) from exc

    session = getattr(result, "session", None)
    auth_user = getattr(result, "user", None)
    if session is None or auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Resposta inválida do provedor de autenticação.",
        )

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == UUID(str(auth_user.id)))
        .one_or_none()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de usuário não encontrado. Contate a coordenação.",
        )
    if profile.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: usuário inativo ou bloqueado.",
        )

    tokens = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_in": getattr(session, "expires_in", 3600),
    }
    return tokens, profile


def logout(access_token: str) -> None:
    """Encerra a sessão no Supabase (revoga o refresh token).

    Falhas silenciosas: mesmo que o Supabase não responda, o frontend deve
    descartar os tokens localmente.
    """
    try:
        admin = get_admin_client()
        admin.auth.admin.sign_out(access_token)
    except Exception:  # noqa: BLE001
        return
