"""Configurações da aplicação carregadas do ambiente."""

from functools import lru_cache

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

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"
    # Regex opcional para liberar varias origens (ex.: previews do Vercel).
    # Exemplo: r"^https://nucleo-juridico-frontend(-[\w-]+)?\.vercel\.app$"
    CORS_ORIGIN_REGEX: str | None = None

    # --- JWT ---
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "authenticated"

    @property
    def cors_origins_list(self) -> list[str]:
        # Normaliza cada origin removendo trailing slash, que browsers nunca enviam.
        return [
            o.strip().rstrip("/")
            for o in self.CORS_ORIGINS.split(",")
            if o.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
