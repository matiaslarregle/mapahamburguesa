"""
Router de sugerencias de edición.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from ..dependencies import get_current_user, get_db_service, verify_turnstile
from ..schemas import SuggestionCreate, SuggestionResponse, MessageResponse
from ..services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/{place_id}/suggestions",
    response_model=SuggestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear sugerencia de edición",
    dependencies=[Depends(verify_turnstile)],
)
async def create_suggestion(
    place_id: UUID,
    payload: SuggestionCreate,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    # Verificar que el local existe
    place = await svc.get_place(place_id)
    if not place or place.get("status") != "approved":
        raise HTTPException(status_code=404, detail="Local no encontrado")

    # Verificar que el campo a editar existe en el local
    if payload.field_name not in place:
        raise HTTPException(
            status_code=400,
            detail=f"El campo '{payload.field_name}' no existe en este local",
        )

    old_value = place.get(payload.field_name)
    old_value_str = str(old_value) if old_value is not None else None

    suggestion = await svc.create_suggestion(
        place_id=place_id,
        suggested_by=current_user["id"],
        field_name=payload.field_name,
        old_value=old_value_str,
        new_value=payload.new_value,
    )
    logger.info(
        f"Sugerencia creada: {payload.field_name} en {place_id} por {current_user['email']}"
    )
    return suggestion
