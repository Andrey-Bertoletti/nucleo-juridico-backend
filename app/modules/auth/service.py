"""Regras de negócio do módulo auth — orquestra o Supabase Auth.

O **cadastro de usuários** acontece via `POST /admin/users` (módulo admin),
que requer perfil `admin_coordenacao`. Não há cadastro público — o sistema
gerencia dados jurídicos sigilosos.
"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.users.models import Profile
from app.services.supabase_client import get_admin_client, get_anon_client


logger = logging.getLogger("nucleo_juridico")


def login(db: Session, email: str, password: str) -> tuple[dict, Profile]:
    """Autentica via Supabase e retorna tokens + profile carregado do banco."""
    client = get_anon_client()
    try:
        result = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:  # noqa: BLE001 — supabase pode lançar várias subclasses
        # Mensagem genérica intencional: não diferenciamos "usuário não existe"
        # de "senha errada" para não habilitar enumeração de contas.
        logger.info("Login negado para %s.", email)
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
        # Vazaríamos a existência da conta no Supabase Auth se respondêssemos
        # algo diferente do login negado normal.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
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


def refresh_session(refresh_token: str) -> dict:
    """Troca um refresh_token por um novo par access/refresh.

    Sem isso, o frontend precisa pedir nova senha ao usuário sempre que o
    access_token (~1h) expira. Aqui delegamos ao Supabase, que emite um
    novo par e revoga o anterior (se `enable_refresh_token_rotation=true`,
    que é o default do projeto).
    """
    client = get_anon_client()
    try:
        result = client.auth.refresh_session(refresh_token)
    except Exception as exc:  # noqa: BLE001
        logger.info("Refresh token rejeitado.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada — entre novamente.",
        ) from exc

    session = getattr(result, "session", None)
    if session is None or not getattr(session, "access_token", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida — entre novamente.",
        )

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token or refresh_token,
        "expires_in": getattr(session, "expires_in", 3600),
    }


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


def request_password_reset(email: str, redirect_to: str | None = None) -> None:
    """Dispara o e-mail de reset de senha via Supabase.

    SEMPRE retorna `None` (mesmo se o e-mail não existir) — chamadores devem
    apresentar mensagem genérica para evitar enumeração de contas.

    Observação: o e-mail só é enviado de fato se o projeto Supabase estiver
    com SMTP configurado (Dashboard → Authentication → SMTP Settings, ou
    `supabase/config.toml` → `[auth.email.smtp]`). Sem SMTP custom, o
    Supabase usa o servidor interno (~4 e-mails/hora, apenas para membros
    do projeto) — é a causa #1 de "o reset não chega".

    Erros do provedor são engolidos para não vazar enumeração, mas
    registrados com `logger.exception` (stack trace completo) para
    diagnóstico — em desenvolvimento, faça `tail -f` no log do uvicorn
    e procure por "Falha ao disparar e-mail de reset".
    """
    try:
        # Não usamos `get_anon_client()` (cached) aqui: se o cliente cacheado
        # estiver em estado inválido, futuros resets também falham. Criar um
        # cliente novo isola cada tentativa.
        client = get_anon_client()
        options: dict[str, str] = {}
        if redirect_to:
            options["redirect_to"] = redirect_to
        if options:
            client.auth.reset_password_for_email(email, options=options)
        else:
            client.auth.reset_password_for_email(email)
        logger.info("E-mail de reset de senha solicitado para %s.", email)
    except Exception:  # noqa: BLE001 — best-effort, mas precisamos do stack
        logger.exception(
            "Falha ao disparar e-mail de reset de senha para %s "
            "(verifique SMTP no Dashboard do Supabase e a lista de "
            "Redirect URLs em Authentication → URL Configuration).",
            email,
        )
