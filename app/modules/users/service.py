"""Regras de negócio do módulo users."""

import logging
import secrets
import string
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.modules.users.models import Profile
from app.modules.users.schemas import UserCreate, UserStatusUpdate, UserUpdate
from app.services.supabase_client import get_admin_client


logger = logging.getLogger("nucleo_juridico")


# Caracteres da senha temporária — excluímos os ambíguos visualmente
# (O/0/o, I/l/1) para o usuário não confundir ao digitar o que veio do papel.
_TEMP_PASSWORD_ALPHABET = (
    "ABCDEFGHJKLMNPQRSTUVWXYZ"
    "abcdefghijkmnpqrstuvwxyz"
    "23456789"
    "!@#$%&*"
)


def _generate_temp_password(length: int = 14) -> str:
    """Gera senha aleatória forte para entregar manualmente ao usuário.

    Garante pelo menos uma maiúscula, uma minúscula, um dígito e um símbolo —
    senão o Supabase pode rejeitar se a política exigir composição.
    """
    while True:
        candidate = "".join(
            secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length)
        )
        if (
            any(c.isupper() for c in candidate)
            and any(c.islower() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in "!@#$%&*" for c in candidate)
        ):
            return candidate


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


def _set_initial_password(auth_user_id: str, password: str) -> None:
    """Define a senha do usuário recém-convidado.

    Usado apenas quando o admin opta por enviar uma senha provisória junto
    com o convite (campo `password` no payload). Como `invite_user_by_email`
    não aceita senha, definimos via `admin.update_user_by_id` logo depois.
    Best-effort: falha aqui não anula o convite (o usuário ainda pode
    definir a senha pelo link do e-mail).
    """
    try:
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(auth_user_id, {"password": password})
    except Exception:  # noqa: BLE001 — best-effort
        logger.exception(
            "Falha ao definir senha provisória para auth_user_id=%s. "
            "O usuário ainda pode definir a senha via link do convite.",
            auth_user_id,
        )


def create_user(db: Session, payload: UserCreate) -> Profile:
    """Cria a conta via `invite_user_by_email` e o profile correspondente.

    Fluxo:
      1. Verifica que o e-mail não está em `profiles` (evita duplicata).
      2. Chama `admin.auth.admin.invite_user_by_email(email, redirect_to=...)`.
         O Supabase cria o `auth.users`, dispara o e-mail de convite e
         marca o e-mail como NÃO confirmado até o usuário clicar no link.
      3. Se o payload trouxer `password`, define-a via `update_user_by_id`
         (best-effort) — útil para uma senha provisória combinada por outro
         canal. Sem isso, o usuário define a senha exclusivamente pelo link.
      4. Persiste o `profile` linkado ao `auth.users.id`. Se a persistência
         falhar, o `auth.users` é removido em rollback compensatório.

    O link no e-mail aponta para `FRONTEND_URL/reset-password` — a mesma
    página usada no fluxo "esqueci minha senha", então não precisamos de
    UI duplicada.
    """
    if db.query(Profile).filter(Profile.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este e-mail.",
        )

    admin = get_admin_client()
    redirect_to = f"{settings.FRONTEND_URL}/reset-password"
    try:
        result = admin.auth.admin.invite_user_by_email(
            payload.email,
            options={
                "redirect_to": redirect_to,
                "data": {"name": payload.name, "role": payload.role},
            },
        )
    except Exception as exc:  # noqa: BLE001 — supabase pode lançar várias subclasses
        # Log detalhado fica no servidor; resposta é genérica para não vazar
        # estrutura interna do Supabase Auth (rate-limit, SMTP, etc.).
        logger.exception(
            "Falha ao convidar usuário %s no Supabase Auth "
            "(verifique SMTP no Dashboard do Supabase e a Redirect URL %s).",
            payload.email,
            redirect_to,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível enviar o convite. Verifique o e-mail e tente novamente.",
        ) from exc

    auth_user = getattr(result, "user", None)
    auth_user_id = getattr(auth_user, "id", None) if auth_user is not None else None
    if auth_user is None or auth_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase não retornou um usuário válido.",
        )

    auth_user_id_str = str(auth_user_id)

    # Senha provisória opcional — não interrompe o fluxo se falhar.
    if payload.password:
        _set_initial_password(auth_user_id_str, payload.password)

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
        logger.info(
            "Convite enviado para %s (auth_user_id=%s).",
            payload.email,
            auth_user_id_str,
        )
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


def reset_password(db: Session, user_id: UUID) -> tuple[Profile, str]:
    """Gera uma senha temporária e aplica via Supabase Admin API.

    Retorna o profile e a senha em CLARO — a senha só é exibida uma vez no
    response e fica com o admin (em papel ou anotação fora do sistema) para
    entregar ao usuário. Não persistimos a senha em nenhum lugar do nosso
    banco.

    Esse fluxo existe pra não depender do e-mail de reset (que falha quando
    o SMTP do Supabase não está configurado), e pra desbloquear quando o
    usuário não consegue receber o link por qualquer razão. Veja
    [[shared-student-login]] — em especial pra resetar o login compartilhado
    do aluno geral periodicamente.
    """
    profile = get_user(db, user_id)
    temp_password = _generate_temp_password()
    try:
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(
            str(profile.user_id), {"password": temp_password}
        )
    except Exception as exc:  # noqa: BLE001 — Supabase pode lançar várias
        logger.exception(
            "Falha ao resetar senha do user_id=%s no Supabase Auth.",
            profile.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível redefinir a senha junto ao provedor de autenticação.",
        ) from exc

    logger.info(
        "Senha redefinida administrativamente para profile %s (email=%s).",
        profile.id,
        profile.email,
    )
    return profile, temp_password
