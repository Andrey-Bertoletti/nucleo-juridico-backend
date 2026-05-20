"""Rotas do módulo auth."""

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import (
    BearerCredentials,
    CurrentUser,
    DbSession,
    bearer_scheme,
    get_current_user,
)
from app.modules.auth import service
from app.modules.auth.schemas import LoginRequest, LoginResponse, MeResponse


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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: BearerCredentials,
    _: CurrentUser = Depends(get_current_user),
) -> Response:
    service.logout(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser) -> MeResponse:
    return current_user  # type: ignore[return-value]
