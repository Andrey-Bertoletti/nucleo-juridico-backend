"""Schemas Pydantic do módulo users."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Role = Literal["aluno_estagiario", "professor_orientador", "admin_coordenacao"]
UserStatus = Literal["ativo", "inativo", "bloqueado"]


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: Role


class UserCreate(UserBase):
    """Criação de usuário — cria conta no Supabase Auth e o profile correspondente.

    `password` é opcional: quando ausente, o backend usa o fluxo de
    `invite_user_by_email`, que envia ao usuário um e-mail com link para
    definir a própria senha (e confirma o e-mail no clique). Esse é o
    caminho recomendado — o admin nunca precisa transmitir senha por
    canal lateral.
    """

    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    role: Role | None = None


class UserStatusUpdate(BaseModel):
    status: UserStatus


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    email: EmailStr
    role: Role
    status: UserStatus
    created_at: datetime
    updated_at: datetime
