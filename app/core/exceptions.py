"""Handlers globais de exceção — padroniza o formato JSON de erro.

Sem isso, exceções não tratadas no FastAPI retornam HTML do Starlette e
vazam stack trace para o cliente em produção. Aqui:

  - Em produção (APP_DEBUG=false) responde 500 com mensagem genérica.
  - Em desenvolvimento (APP_DEBUG=true) inclui o tipo + mensagem da
    exceção para facilitar o debug.

Erros já lançados como `HTTPException` continuam fluindo normalmente
(FastAPI tem handler próprio para eles).

Segurança: o log do servidor mascara o cabeçalho Authorization e
qualquer outro header que carregue credenciais — evita gravar tokens em
arquivos de log que podem ser replicados externamente.
"""

import logging
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.settings import settings


logger = logging.getLogger("nucleo_juridico")


_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "proxy-authorization",
}
_CPF_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_TOKEN_PATTERN = re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}")


def _redact(text: str | None) -> str:
    """Mascara CPFs e tokens JWT em mensagens livres antes de logar."""
    if not text:
        return ""
    redacted = _TOKEN_PATTERN.sub("<jwt-redacted>", text)
    redacted = _CPF_PATTERN.sub("<cpf-redacted>", redacted)
    return redacted


def _safe_headers(request: Request) -> dict[str, str]:
    safe: dict[str, str] = {}
    for name, value in request.headers.items():
        if name.lower() in _SENSITIVE_HEADERS:
            safe[name] = "<redacted>"
        else:
            safe[name] = value
    return safe


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "Unhandled exception at %s %s | headers=%s",
        request.method,
        request.url.path,
        _safe_headers(request),
        exc_info=exc,
    )
    if settings.APP_DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Erro interno: {type(exc).__name__}: {_redact(str(exc))}"},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."},
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, unhandled_exception_handler)
