"""Entrada da aplicação FastAPI — registra middlewares, routers e healthcheck."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.modules.auth.router import router as auth_router
from app.modules.clients.router import router as clients_router
from app.modules.users.router import router as users_router


app = FastAPI(
    title="Núcleo Jurídico API",
    description=(
        "API do Sistema de Gestão de Atendimento Jurídico. "
        "Documentação interativa em `/docs` e schema OpenAPI em `/openapi.json`."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(clients_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
