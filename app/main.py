"""
Entrada da aplicação FastAPI.

Esta é a estrutura inicial do Sistema de Gestão de Atendimento Jurídico.
Os módulos de domínio (atendimento, clientes, casos, etc.) serão registrados
em `app/modules/` e incluídos aqui via `app.include_router(...)`.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Núcleo Jurídico API",
    description="API do Sistema de Gestão de Atendimento Jurídico.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Endpoint simples de verificação de saúde."""
    return {"status": "ok"}
