"""Rotas do módulo auth.

Cadastro de usuários **não** é público: somente um `admin_coordenacao`
pode criar contas via `POST /admin/users`. Esta decisão é intencional —
o sistema lida com dados jurídicos sigilosos e o acesso é restrito.
"""

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.core.dependencies import BearerCredentials, CurrentUser, DbSession
from app.core.rate_limit import enforce_login_rate_limit, reset_login_rate_limit
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    redirect_to: str | None = Field(default=None, max_length=500)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> LoginResponse:
    # Rate-limit por (IP, email) — mitiga brute-force credencial.
    rate_key = enforce_login_rate_limit(request, payload.email)
    tokens, profile = service.login(db, payload.email, payload.password)
    # Login OK → libera o budget para esse par.
    reset_login_rate_limit(rate_key)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        user=profile,  # type: ignore[arg-type]
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest) -> RefreshResponse:
    """Troca um refresh_token por novo par access/refresh.

    Endpoint público (não exige Bearer) — o frontend chama quando o
    access_token está prestes a expirar. O Supabase faz a validação do
    refresh_token e rotaciona se `enable_refresh_token_rotation=true`.
    """
    tokens = service.refresh_session(payload.refresh_token)
    return RefreshResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest) -> dict[str, str]:
    """Inicia recuperação de senha — resposta SEMPRE genérica.

    Por segurança (evitar enumeração de contas), respondemos `202` e a
    mesma mensagem independente de o e-mail existir ou não. O Supabase
    é quem decide se envia o e-mail.
    """
    service.request_password_reset(payload.email, payload.redirect_to)
    return {
        "detail": (
            "Se houver uma conta vinculada ao e-mail informado, "
            "as instruções para redefinir a senha serão enviadas."
        )
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: BearerCredentials,
    _: CurrentUser,
) -> Response:
    service.logout(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser) -> MeResponse:
    return current_user  # type: ignore[return-value]
