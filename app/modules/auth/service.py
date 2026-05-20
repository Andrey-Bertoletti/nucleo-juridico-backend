"""Regras de negócio do módulo auth — orquestra o Supabase Auth."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.users.models import Profile
from app.services.supabase_client import get_admin_client, get_anon_client


DEFAULT_REGISTER_ROLE = "aluno_estagiario"


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
            detail="Perfil de usuário não encontrado.",
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


def register(
    db: Session, name: str, email: str, password: str
) -> tuple[dict | None, Profile]:
    """Cadastra um novo usuário com perfil padrão `aluno_estagiario`.

    Se a confirmação de e-mail estiver habilitada no Supabase, `session` será
    `None` — neste caso o frontend deve instruir o usuário a confirmar o
    e-mail antes de entrar.
    """
    if db.query(Profile).filter(Profile.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este e-mail.",
        )

    client = get_anon_client()
    try:
        result = client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": {"name": name}},
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível criar a conta: {exc}",
        ) from exc

    auth_user = getattr(result, "user", None)
    if auth_user is None or getattr(auth_user, "id", None) is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase não retornou um usuário válido.",
        )

    profile = Profile(
        user_id=UUID(str(auth_user.id)),
        name=name,
        email=email,
        role=DEFAULT_REGISTER_ROLE,
        status="ativo",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    session = getattr(result, "session", None)
    if session is None:
        # Confirmação de e-mail necessária — sem auto-login.
        return None, profile

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
