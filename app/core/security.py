"""Validação de JWT emitido pelo Supabase Auth."""

import jwt
from fastapi import HTTPException, status

from app.core.settings import settings


def decode_supabase_jwt(token: str) -> dict:
    """Decodifica e valida um JWT emitido pelo Supabase.

    O Supabase assina tokens com `SUPABASE_JWT_SECRET` (HS256 por padrão) e
    inclui a audience `authenticated` para sessões de usuário.
    """
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
