"""
Dependencias de FastAPI: auth, permisos, etc.
"""
import logging
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from .config import settings
from .database import get_supabase_admin

logger = logging.getLogger(__name__)

# auto_error=False → devolvemos nuestro propio 401 con mensaje en español
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase: Client = Depends(get_supabase_admin),
) -> dict:
    """
    Valida el JWT de Supabase y devuelve el usuario + su profile.
    Lanza 401 si no hay token, es inválido, o el perfil no existe.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Supabase valida firma + expiración del JWT
        user_response = supabase.auth.get_user(credentials.credentials)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )

        user = user_response.user

        # Traemos el profile asociado
        profile_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user.id)
            .single()
            .execute()
        )

        if not profile_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de usuario no encontrado",
            )

        profile = profile_resp.data

        return {
            "id": user.id,
            "email": user.email,
            "name": profile.get("name"),
            "avatar_url": profile.get("avatar_url"),
            "role": profile.get("role", "user"),
            "is_active": profile.get("is_active", True),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al validar el token de autenticación",
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase: Client = Depends(get_supabase_admin),
) -> Optional[dict]:
    """
    Variante "soft": devuelve el usuario si hay token válido, o None si no.
    Útil para endpoints donde la auth es opcional (ej. /places público).
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, supabase)
    except HTTPException:
        return None


async def get_moderator_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Requiere rol admin o moderator."""
    if current_user.get("role") not in ("admin", "moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de moderador o administrador",
        )
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    return current_user


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Requiere rol admin únicamente."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user

# Pegar al final de backend/dependencies.py

from functools import lru_cache
from supabase import Client as SupabaseClient
from .database import get_supabase_admin
from .services.supabase_service import SupabaseService
from .services.storage_service import StorageService


def get_db() -> SupabaseClient:
    """Devuelve el cliente Supabase admin."""
    return get_supabase_admin()


def get_db_service(db: SupabaseClient = None) -> SupabaseService:
    return SupabaseService(db or get_supabase_admin())


def get_storage(db: SupabaseClient = None) -> StorageService:
    return StorageService(db or get_supabase_admin())


# =============================================================================
# Cloudflare Turnstile dependency
# =============================================================================
from fastapi import Request
from .services.turnstile_service import TurnstileService, get_turnstile_service


async def verify_turnstile(
    request: Request,
    svc: TurnstileService = Depends(get_turnstile_service),
) -> bool:
    """
    Dependency que valida el token de Turnstile enviado en el header
    `cf-turnstile-token` o en el body `cf_turnstile_token`.
    Lanza 403 si el token es inválido.
    """
    # Buscar token en header o body/form.
    token = request.headers.get("cf-turnstile-token")

    if not token and request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        try:
            if "application/json" in content_type:
                body = await request.json()
                token = body.get("cf_turnstile_token") if body else None
            elif (
                "multipart/form-data" in content_type
                or "application/x-www-form-urlencoded" in content_type
            ):
                form = await request.form()
                token = form.get("cf_turnstile_token")
        except Exception:
            pass

    if not token:
        if not svc.enabled and settings.TURNSTILE_FAIL_OPEN:
            logger.warning(
                "TURNSTILE sin token y sin secret key — fail-open activado"
            )
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Falta el token de Turnstile (cf-turnstile-token)",
        )

    # IP del cliente (Cloudflare suele mandar CF-Connecting-IP)
    remote_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )

    ok = await svc.verify(token, remote_ip=remote_ip)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verificación de Turnstile fallida",
        )
    return True
