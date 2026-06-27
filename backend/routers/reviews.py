"""
Router de reviews: 1 review por usuario por local.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from ..dependencies import get_current_user, get_db_service, verify_turnstile
from ..schemas import (
    ReviewCreate, ReviewUpdate, ReviewResponse, ReviewWithUser, MessageResponse,
)
from ..services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()


# ====================== LIST reviews de un local ======================
@router.get(
    "/{place_id}/reviews",
    response_model=list[ReviewWithUser],
    summary="Reviews de un local",
)
async def list_reviews(
    place_id: UUID,
    svc: SupabaseService = Depends(get_db_service),
):
    return await svc.list_reviews(place_id)


# ====================== POST crear review ======================
@router.post(
    "/{place_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear review",
    dependencies=[Depends(verify_turnstile)],
)
async def create_review(
    place_id: UUID,
    payload: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    # Verificar que el local existe y está aprobado
    place = await svc.get_place(place_id)
    if not place or place.get("status") != "approved":
        raise HTTPException(status_code=404, detail="Local no encontrado")

    # Verificar que no exista ya una review del mismo usuario
    existing = await svc.get_user_review(place_id, current_user["id"])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya dejaste una review en este local. Usá PUT para editarla.",
        )

    review = await svc.create_review(
        place_id=place_id,
        user_id=current_user["id"],
        rating=payload.rating,
        comment=payload.comment,
    )
    # Marcar el local como visitado automáticamente
    await svc.mark_visited(current_user["id"], place_id)
    logger.info(f"Review creada en {place_id} por {current_user['email']}")
    return review


# ====================== PUT editar review propia ======================
@router.put(
    "/{place_id}/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Editar review propia",
)
async def update_review(
    place_id: UUID,
    review_id: UUID,
    payload: ReviewUpdate,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    # Traer review para verificar ownership
    all_reviews = await svc.list_reviews(place_id)
    review = next((r for r in all_reviews if r["id"] == str(review_id)), None)
    if not review:
        raise HTTPException(status_code=404, detail="Review no encontrada")

    is_owner = review["user_id"] == str(current_user["id"])
    is_admin = current_user.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Solo podés editar tu propia review")

    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Sin cambios para aplicar")

    return await svc.update_review(review_id, data["rating"], data.get("comment"))


# ====================== DELETE review ======================
@router.delete(
    "/{place_id}/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Borrar review",
)
async def delete_review(
    place_id: UUID,
    review_id: UUID,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    all_reviews = await svc.list_reviews(place_id)
    review = next((r for r in all_reviews if r["id"] == str(review_id)), None)
    if not review:
        raise HTTPException(status_code=404, detail="Review no encontrada")

    is_owner = review["user_id"] == str(current_user["id"])
    is_admin = current_user.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Sin permiso para borrar esta review")

    ok = await svc.delete_review(review_id)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo borrar la review")
    return MessageResponse(message="Review eliminada")
