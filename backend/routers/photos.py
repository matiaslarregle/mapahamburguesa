"""
Router de fotos: upload, listado, delete, marcar portada.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from ..config import settings
from ..dependencies import get_current_user, get_db_service, get_storage, verify_turnstile
from ..schemas import PhotoResponse, MessageResponse
from ..services.supabase_service import SupabaseService
from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


# ====================== LIST fotos ======================
@router.get(
    "/{place_id}/photos",
    response_model=list[PhotoResponse],
    summary="Fotos de un local",
)
async def list_photos(
    place_id: UUID,
    svc: SupabaseService = Depends(get_db_service),
):
    return await svc.list_photos(place_id)


# ====================== POST upload ======================
@router.post(
    "/{place_id}/photos",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir una foto",
    dependencies=[Depends(verify_turnstile)],
)
async def upload_photo(
    place_id: UUID,
    file: UploadFile = File(..., description="Imagen (jpg/png/webp, máx 8MB)"),
    is_cover: bool = Form(False),
    review_id: str = Form(None),
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
    storage: StorageService = Depends(get_storage),
):
    # 1) Verificar local
    place = await svc.get_place(place_id)
    if not place or place.get("status") != "approved":
        raise HTTPException(status_code=404, detail="Local no encontrado")

    # 2) Verificar límite de 10 fotos
    current_count = await svc.count_photos(place_id)
    if current_count >= settings.MAX_PHOTOS_PER_PLACE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este local ya tiene el máximo de {settings.MAX_PHOTOS_PER_PLACE} fotos",
        )

    # 3) Leer contenido
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    # 4) Subir a Storage (valida + redimensiona adentro)
    try:
        public_url = await storage.upload_photo(
            place_id=place_id,
            user_id=current_user["id"],
            file_content=content,
            filename=file.filename or "photo.jpg",
            content_type=file.content_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error subiendo foto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al subir la foto")

    # 5) Si es cover, desmarcar las otras
    if is_cover:
        # Necesitamos el ID de la foto a crear — lo creamos y después la marcamos
        photo = await svc.create_photo(place_id, current_user["id"], public_url, False, UUID(review_id) if review_id else None)
        await svc.set_cover_photo(place_id, photo["id"])
        photo["is_cover"] = True
        return photo

    # 6) Si era la primera foto, la marcamos automáticamente como cover
    photo = await svc.create_photo(place_id, current_user["id"], public_url, is_cover, UUID(review_id) if review_id else None)
    if current_count == 0:
        await svc.set_cover_photo(place_id, photo["id"])
        photo["is_cover"] = True

    return photo


# ====================== DELETE foto ======================
@router.delete(
    "/{place_id}/photos/{photo_id}",
    response_model=MessageResponse,
    summary="Borrar foto",
)
async def delete_photo(
    place_id: UUID,
    photo_id: UUID,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
    storage: StorageService = Depends(get_storage),
):
    photos = await svc.list_photos(place_id)
    photo = next((p for p in photos if p["id"] == str(photo_id)), None)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    is_owner = photo["user_id"] == str(current_user["id"])
    is_admin = current_user.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Sin permiso para borrar esta foto")

    # 1) Borrar de DB
    await svc.delete_photo(photo_id)
    # 2) Borrar de Storage (best-effort)
    await storage.delete_photo(photo["url"])

    return MessageResponse(message="Foto eliminada")


# ====================== PATCH cover (admin) ======================
@router.patch(
    "/{place_id}/photos/{photo_id}/cover",
    response_model=PhotoResponse,
    summary="Marcar foto como portada (admin)",
)
async def set_cover(
    place_id: UUID,
    photo_id: UUID,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden cambiar la portada")

    photo = await svc.set_cover_photo(place_id, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    return photo
