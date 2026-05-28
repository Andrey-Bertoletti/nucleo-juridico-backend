"""Configurações da aplicação carregadas do ambiente."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Aplicação ---
    APP_NAME: str = "nucleo-juridico-backend"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # --- Banco ---
    DATABASE_URL: str

    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_STORAGE_BUCKET: str = "documentos"

    # --- Frontend ---
    # URL pública do frontend, usada para construir os links que aparecem nos
    # e-mails (convite de novo usuário, reset de senha quando o frontend não
    # passa um `redirect_to` explícito). Sem essa URL, os links caem na
    # `Site URL` configurada no Dashboard do Supabase — em ambientes com
    # múltiplos deploys (preview, produção), isso costuma vazar o usuário
    # para a URL errada.
    FRONTEND_URL: str = "http://localhost:3000"
    # Lista opcional de redirects EXATOS permitidos para fluxos de e-mail
    # do Supabase Auth. Se vazia, o backend permite apenas
    # `{FRONTEND_URL}/reset-password`.
    AUTH_ALLOWED_REDIRECT_URLS: str = ""

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"
    # Regex opcional para liberar varias origens (ex.: previews do Vercel).
    # Exemplo: r"^https://nucleo-juridico-frontend(-[\w-]+)?\.vercel\.app$"
    CORS_ORIGIN_REGEX: str | None = None

    # --- JWT ---
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "authenticated"

    @field_validator("DATABASE_URL")
    @classmethod
    def _ensure_psycopg_driver(cls, value: str) -> str:
        """Garante que o driver psycopg3 seja usado pelo SQLAlchemy.

        Strings copiadas do Supabase vêm como `postgresql://...`. Sem o
        prefixo `+psycopg`, o SQLAlchemy tenta o driver `psycopg2` (não
        instalado) e o serviço quebra na primeira conexão. Aqui fazemos
        o ajuste automático.
        """
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]
        if value.startswith("postgres://"):  # alias usado por algumas plataformas
            return "postgresql+psycopg://" + value[len("postgres://") :]
        return value

    @field_validator("SUPABASE_URL", "FRONTEND_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origins_list(self) -> list[str]:
        # Normaliza cada origin removendo trailing slash, que browsers nunca enviam.
        return [
            o.strip().rstrip("/")
            for o in self.CORS_ORIGINS.split(",")
            if o.strip()
        ]

    @property
    def auth_allowed_redirect_urls_list(self) -> list[str]:
        configured = [
            o.strip().rstrip("/")
            for o in self.AUTH_ALLOWED_REDIRECT_URLS.split(",")
            if o.strip()
        ]
        default_reset = f"{self.FRONTEND_URL}/reset-password"
        return list(dict.fromkeys([default_reset, *configured]))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
