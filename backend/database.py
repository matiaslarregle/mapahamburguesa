"""
Cliente Supabase.
- get_supabase_admin()  → usa SERVICE_ROLE_KEY, SOLO en backend.
- get_supabase_anon()    → usa ANON_KEY, útil para llamadas públicas.
"""
from functools import lru_cache
from supabase import create_client, Client
from .config import settings


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Cliente con permisos elevados. NUNCA exponer al frontend."""
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )


@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    """Cliente con permisos de usuario anónimo."""
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
    )
