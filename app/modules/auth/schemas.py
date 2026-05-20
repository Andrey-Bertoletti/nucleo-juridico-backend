"""Schemas Pydantic do módulo auth."""

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.schemas import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    requires_email_confirmation: bool = False


MeResponse = UserResponse
