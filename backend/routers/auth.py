"""
Router de autenticación con Supabase.
Google OAuth + endpoint /me + logout.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from supabase import Client
from ..config import settings
from ..database import get_supabase_admin, get_supabase_anon
from ..dependencies import get_current_user
from ..schemas import AuthMeResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ====================== Google OAuth (init) ======================
@router.get("/google", response_model=MessageResponse, summary="Iniciar OAuth con Google")
async def login_google():
    """
    Redirige al usuario a la pantalla de Google OAuth gestionada por Supabase.
    El callback de Supabase redirige a /auth/callback.
    """
    supabase = get_supabase_anon()
    try:
        res = supabase.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {
                    "redirect_to": f"{settings.FRONTEND_URL}/auth/callback.html",
                },
            }
        )
        return MessageResponse(
            message=f"Redirigir a: {res.url}", success=True
        )
    except Exception as e:
        logger.error(f"Error iniciando OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo iniciar el flujo de OAuth con Google",
        )


# ====================== OAuth callback ======================
@router.get("/callback", summary="Callback de OAuth")
async def auth_callback(
    code: str = Query(..., description="Authorization code de Supabase"),
    next: str = Query("/"),
    supabase: Client = Depends(get_supabase_admin),
):
    """
    Recibe el `code` de Supabase, lo intercambia por una sesión,
    y redirige al frontend con el access_token en la URL.
    """
    try:
        session_res = supabase.auth.exchange_code_for_session({"auth_code": code})
        if not session_res or not session_res.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener la sesión",
            )

        access_token = session_res.session.access_token
        user = session_res.user

        # Crear/actualizar profile si no existe
        existing = (
            supabase.table("profiles")
            .select("id")
            .eq("id", user.id)
            .execute()
        )
        if not existing.data:
            name = (
                user.user_metadata.get("full_name")
                or user.user_metadata.get("name")
                or user.email.split("@")[0]
            )
            avatar = user.user_metadata.get("avatar_url") or user.user_metadata.get("picture")
            supabase.table("profiles").insert(
                {
                    "id": user.id,
                    "name": name,
                    "avatar_url": avatar,
                    "role": "user",
                    "is_active": True,
                }
            ).execute()

        # Redirigir al frontend con el token
        redirect_url = f"{settings.FRONTEND_URL}{next}#access_token={access_token}"
        return RedirectResponse(url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en callback OAuth: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar el callback de autenticación",
        )


# ====================== Me ======================
@router.get("/me", response_model=AuthMeResponse, summary="Usuario actual")
async def get_me(current_user: dict = Depends(get_current_user)):
    return AuthMeResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        avatar_url=current_user.get("avatar_url"),
        role=current_user["role"],
        is_active=current_user.get("is_active", True),
    )


# ====================== Logout ======================
@router.post("/logout", response_model=MessageResponse, summary="Cerrar sesión")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout "soft" — el frontend debe descartar el token.
    Supabase no tiene un endpoint de logout server-side que invalide el token
    en todas las sesiones, pero podemos marcar la sesión actual como revocada.
    """
    # Por ahora solo devolvemos OK. El frontend limpia localStorage.
    logger.info(f"Logout de usuario {current_user['id']}")
    return MessageResponse(message="Sesión cerrada. Limpiá el token en el cliente.")


