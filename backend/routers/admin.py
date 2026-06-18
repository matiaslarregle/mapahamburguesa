"""
Router de administración: aprobar/rechazar locales y sugerencias, stats.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from ..dependencies import get_admin_user, get_moderator_user, get_db_service
from ..schemas import PlaceResponse, SuggestionResponse, MessageResponse
from ..services.supabase_service import SupabaseService
from ..services.email_service import EmailService, get_email_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ====================== Stats dashboard ======================
@router.get("/stats", summary="Estadísticas globales (admin)")
async def get_stats(
    _user: dict = Depends(get_admin_user),
    svc: SupabaseService = Depends(get_db_service),
):
    return await svc.admin_stats()


# ====================== Locales pendientes ======================
@router.get(
    "/places/pending",
    response_model=list[PlaceResponse],
    summary="Locales pendientes de moderación",
)
async def list_pending_places(
    _user: dict = Depends(get_moderator_user),
    svc: SupabaseService = Depends(get_db_service),
):
    return await svc.list_places(status="pending", limit=200, offset=0)


# ====================== Aprobar local ======================
@router.patch(
    "/places/{place_id}/approve",
    response_model=PlaceResponse,
    summary="Aprobar local",
)
async def approve_place(
    place_id: UUID,
    current_user: dict = Depends(get_moderator_user),
    svc: SupabaseService = Depends(get_db_service),
    email_svc: EmailService = Depends(get_email_service),
):
    place = await svc.approve_place(place_id, approved_by=current_user["id"])
    if not place:
        raise HTTPException(status_code=404, detail="Local no encontrado")

    # Notificar al autor por email
    added_by = place.get("added_by")
    if added_by:
        # Para no acoplarnos a Supabase Auth acá, simplemente logueamos
        logger.info(f"Local aprobado: {place['name']} (id={place_id})")
        # email_svc.send_email(...) se puede activar si guardamos el email en el profile

    return place


# ====================== Rechazar local ======================
@router.patch(
    "/places/{place_id}/reject",
    response_model=MessageResponse,
    summary="Rechazar local",
)
async def reject_place(
    place_id: UUID,
    _user: dict = Depends(get_moderator_user),
    svc: SupabaseService = Depends(get_db_service),
):
    place = await svc.get_place(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    await svc.reject_place(place_id)
    return MessageResponse(message=f"Local '{place['name']}' rechazado")


# ====================== Sugerencias pendientes ======================
@router.get(
    "/suggestions/pending",
    response_model=list[SuggestionResponse],
    summary="Sugerencias pendientes",
)
async def list_pending_suggestions(
    _user: dict = Depends(get_moderator_user),
    svc: SupabaseService = Depends(get_db_service),
):
    return await svc.list_pending_suggestions()


# ====================== Aprobar sugerencia ======================
@router.patch(
    "/suggestions/{suggestion_id}/approve",
    response_model=MessageResponse,
    summary="Aprobar sugerencia (aplica el cambio)",
)
async def approve_suggestion(
    suggestion_id: UUID,
    current_user: dict = Depends(get_moderator_user),
    svc: SupabaseService = Depends(get_db_service),
):
    # 1) Traer la sugerencia
    all_pending = await svc.list_pending_suggestions()
    suggestion = next(
        (s for s in all_pending if s["id"] == str(suggestion_id)), None
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada o ya resuelta")

    # 2) Aplicar el cambio al local
    update_data = {suggestion["field_name"]: suggestion["new_value"]}
    await svc.update_place(suggestion["place_id"], update_data)

    # 3) Marcar la sugerencia como aprobada
    await svc.resolve_suggestion(suggestion_id, approved=True, reviewed_by=current_user["id"])

    return MessageResponse(message="Sugerencia aprobada y aplicada al local")


# ====================== Rechazar sugerencia ======================
@router.patch(
    "/suggestions/{suggestion_id}/reject",
    response_model=MessageResponse,
    summary="Rechazar sugerencia",
)
async def reject_suggestion(
    suggestion_id: UUID,
    current_user: dict = Depends(get_moderator_user),
    svc: SupabaseService = Depends(get_db_service),
):
    await svc.resolve_suggestion(suggestion_id, approved=False, reviewed_by=current_user["id"])
    return MessageResponse(message="Sugerencia rechazada")

