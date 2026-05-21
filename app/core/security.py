"""Validação de JWT emitido pelo Supabase Auth.

Suporta:
  - HS256 (legacy): assinado com `SUPABASE_JWT_SECRET` (chave simétrica).
  - ES256/RS256 (padrão dos projetos atuais): assinatura assimétrica; a
    chave pública é obtida no endpoint `/auth/v1/.well-known/jwks.json`.

O algoritmo é detectado lendo o header do token e o caminho é despachado
automaticamente.
"""

from functools import lru_cache

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.core.settings import settings


_ASYMMETRIC_ALGS = {"ES256", "ES384", "ES512", "RS256", "RS384", "RS512"}


@lru_cache
def _jwks_client() -> PyJWKClient:
    """Cliente JWKS para chaves públicas do Supabase (cacheado em memória)."""
    base = settings.SUPABASE_URL.rstrip("/")
    jwks_url = f"{base}/auth/v1/.well-known/jwks.json"
    # cache_keys=True + lifespan=1800s evita ir buscar JWKS a cada request.
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=1800)


def decode_supabase_jwt(token: str) -> dict:
    """Decodifica e valida um JWT do Supabase."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mal formado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    alg: str = header.get("alg", settings.JWT_ALGORITHM)

    try:
        if alg == "HS256":
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=settings.JWT_AUDIENCE,
            )

        if alg in _ASYMMETRIC_ALGS:
            try:
                signing_key = (
                    _jwks_client().get_signing_key_from_jwt(token).key
                )
            except Exception as exc:  # noqa: BLE001 — várias falhas possíveis
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Não foi possível obter as chaves públicas do Supabase "
                        f"({type(exc).__name__})."
                    ),
                ) from exc

            return jwt.decode(
                token,
                signing_key,
                algorithms=[alg],
                audience=settings.JWT_AUDIENCE,
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Algoritmo de assinatura '{alg}' não suportado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura do token inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Audience do token diferente do esperado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc.__class__.__name__}.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
