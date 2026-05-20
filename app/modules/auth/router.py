"""Rotas do módulo auth."""

from fastapi import APIRouter, Response, status

from app.core.dependencies import BearerCredentials, CurrentUser, DbSession
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    tokens, profile = service.login(db, payload.email, payload.password)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        user=profile,  # type: ignore[arg-type]
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    tokens, profile = service.register(
        db, payload.name, payload.email, payload.password
    )
    return RegisterResponse(
        user=profile,  # type: ignore[arg-type]
        access_token=tokens["access_token"] if tokens else None,
        refresh_token=tokens["refresh_token"] if tokens else None,
        expires_in=tokens["expires_in"] if tokens else None,
        requires_email_confirmation=tokens is None,
    )


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
