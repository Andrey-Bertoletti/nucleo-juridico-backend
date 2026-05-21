"""Entrada da aplicação FastAPI — registra middlewares, routers e healthcheck."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.modules.attendances.router import router as attendances_router
from app.modules.auth.router import router as auth_router
from app.modules.catalogs.router import router as catalogs_router
from app.modules.clients.router import router as clients_router
from app.modules.documents.router import router as documents_router
from app.modules.triage.router import router as triage_router
from app.modules.users.router import router as users_router


app = FastAPI(
    title="Núcleo Jurídico API",
    description=(
        "API do Sistema de Gestão de Atendimento Jurídico. "
        "Documentação interativa em `/docs` e schema OpenAPI em `/openapi.json`."
    ),
    version="0.1.0",
)

_cors_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_origins": settings.cors_origins_list,
}
if settings.CORS_ORIGIN_REGEX:
    _cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **_cors_kwargs)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(clients_router)
app.include_router(attendances_router)
app.include_router(triage_router)
app.include_router(documents_router)
app.include_router(catalogs_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
