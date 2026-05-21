"""Handlers globais de exceção — padroniza o formato JSON de erro.

Sem isso, exceções não tratadas no FastAPI retornam HTML do Starlette e
vazam stack trace para o cliente em produção. Aqui:

  - Em produção (APP_DEBUG=false) responde 500 com mensagem genérica.
  - Em desenvolvimento (APP_DEBUG=true) inclui o tipo + mensagem da
    exceção para facilitar o debug.

Erros já lançados como `HTTPException` continuam fluindo normalmente
(FastAPI tem handler próprio para eles).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.settings import settings


logger = logging.getLogger("nucleo_juridico")


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Unhandled exception at %s %s",
        request.method,
        request.url.path,
    )
    if settings.APP_DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Erro interno: {type(exc).__name__}: {exc}"},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."},
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, unhandled_exception_handler)
