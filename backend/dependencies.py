"""
Dependencias de FastAPI: auth, permisos, etc.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings
from .database import get_supabase_admin
from .services.supabase_service import SupabaseService
from .services.storage_service import StorageService
from .services.turnstile_service import TurnstileService, get_turnstile_service


logger = logging.getLogger(__name__)


# auto_error=False → devolvemos nuestro propio 401 con mensaje en español
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase=Depends(get_supabase_admin),
) -> dict:
    """
    Valida el JWT de Supabase y devuelve el usuario + su profile.
    """

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_response = supabase.auth.get_user(
            credentials.credentials
        )

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )

        user = user_response.user

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
        logger.error(
            f"Error validando token: {e}",
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al validar el token de autenticación",
        )



async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase=Depends(get_supabase_admin),
) -> Optional[dict]:
    """
    Usuario opcional.
    """

    if not credentials:
        return None

    try:
        return await get_current_user(
            credentials,
            supabase
        )

    except HTTPException:
        return None



async def get_moderator_user(
    current_user: dict = Depends(get_current_user)
) -> dict:

    if current_user.get("role") not in (
        "admin",
        "moderator"
    ):
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



async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:

    if current_user.get("role") != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )

    return current_user



# ===========================
# Supabase helpers
# ===========================


def get_db():
    """
    Devuelve cliente Supabase admin.
    """
    return get_supabase_admin()



def get_db_service(
    db=None
) -> SupabaseService:

    return SupabaseService(
        db or get_supabase_admin()
    )



def get_storage(
    db=None
) -> StorageService:

    return StorageService(
        db or get_supabase_admin()
    )



# ===========================
# Cloudflare Turnstile
# ===========================


async def verify_turnstile(
    request: Request,
    svc: TurnstileService = Depends(get_turnstile_service),
) -> bool:

    token = request.headers.get(
        "cf-turnstile-token"
    )


    if (
        not token
        and request.method in ("POST", "PUT", "PATCH")
    ):

        content_type = request.headers.get(
            "content-type",
            ""
        )

        try:

            if "application/json" in content_type:

                body = await request.json()

                token = (
                    body.get("cf_turnstile_token")
                    if body
                    else None
                )


            elif (
                "multipart/form-data" in content_type
                or "application/x-www-form-urlencoded" in content_type
            ):

                form = await request.form()

                token = form.get(
                    "cf_turnstile_token"
                )


        except Exception:
            pass



    if not token:

        if (
            not svc.enabled
            and settings.TURNSTILE_FAIL_OPEN
        ):

            logger.warning(
                "TURNSTILE sin token — fail-open activado"
            )

            return True


        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Falta el token de Turnstile",
        )



    remote_ip = (
        request.headers.get(
            "cf-connecting-ip"
        )
        or request.headers.get(
            "x-forwarded-for",
            ""
        ).split(",")[0].strip()
        or (
            request.client.host
            if request.client
            else None
        )
    )


    ok = await svc.verify(
        token,
        remote_ip=remote_ip
    )


    if not ok:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verificación de Turnstile fallida",
        )


    return True
