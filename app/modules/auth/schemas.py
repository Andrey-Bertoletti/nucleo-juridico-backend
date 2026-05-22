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


MeResponse = UserResponse
