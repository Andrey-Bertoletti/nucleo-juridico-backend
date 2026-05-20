"""Wrappers em torno do supabase-py.

Mantemos dois clientes:
- `get_anon_client()`: usa a chave anônima — autenticação de usuários.
- `get_admin_client()`: usa a service_role key — criação/admin de usuários.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.settings import settings


@lru_cache
def get_anon_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache
def get_admin_client() -> Client:
    """Cliente com privilégios de service_role — NUNCA expor ao frontend."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
