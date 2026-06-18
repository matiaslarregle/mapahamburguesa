"""
Router de locales: listado, detalle, creación y edición.
"""
import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from ..config import settings
from ..dependencies import get_current_user, get_db, get_db_service, verify_turnstile
from ..schemas import (
    PlaceCreate, PlaceUpdate, PlaceResponse, PlaceListResponse, MessageResponse,
)
from ..services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()


# ====================== LIST público ======================
@router.get("/", response_model=PlaceListResponse, summary="Listar locales aprobados")
async def list_places(
    partido: Optional[str] = Query(None, description="Filtrar por partido"),
    city: Optional[str] = Query(None),
    place_type: Optional[str] = Query(None),
    price_range: Optional[str] = Query(None),
    has_delivery: Optional[bool] = Query(None),
    payment_method: Optional[str] = Query(None, description="Método de pago aceptable"),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=100),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Client = Depends(get_db),
    svc: SupabaseService = Depends(get_db_service),
):
    # Si pasaron lat+lng, usar búsqueda por proximidad
    if lat is not None and lng is not None:
        items = await svc.search_nearby(lat=lat, lng=lng, radius_km=radius_km, limit=limit)
        # Aplicar filtros extra post-query si los hay
        if partido:        items = [i for i in items if i.get("partido") == partido]
        if place_type:     items = [i for i in items if i.get("place_type") == place_type]
        if price_range:    items = [i for i in items if i.get("price_range") == price_range]
        if has_delivery is not None:
            items = [i for i in items if i.get("has_delivery") == has_delivery]
        total = len(items)
    else:
        items = await svc.list_places(
            status="approved",
            partido=partido, city=city,
            place_type=place_type, price_range=price_range,
            has_delivery=has_delivery, payment_method=payment_method,
            limit=limit, offset=offset,
        )
        total = await svc.count_places(
            status="approved",
            partido=partido, city=city, place_type=place_type,
        )

    return PlaceListResponse(items=items, total=total, limit=limit, offset=offset)


# ====================== GET detalle ======================
@router.get("/{place_id}", response_model=PlaceResponse, summary="Detalle de un local")
async def get_place(
    place_id: UUID,
    svc: SupabaseService = Depends(get_db_service),
):
    place = await svc.get_place(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    if place.get("status") != "approved":
        raise HTTPException(status_code=404, detail="Local no disponible")
    return place


# ====================== POST crear ======================
@router.post(
    "/",
    response_model=PlaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un local (queda pending)",
    dependencies=[Depends(verify_turnstile)],
)
async def create_place(
    payload: PlaceCreate,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    data = payload.model_dump()
    place = await svc.create_place(data, added_by=current_user["id"])
    logger.info(f"Local creado: {place.get('name')} por {current_user['email']}")
    return place


# ====================== PUT editar (admin) ======================
@router.put("/{place_id}", response_model=PlaceResponse, summary="Editar local (admin)")
async def update_place(
    place_id: UUID,
    payload: PlaceUpdate,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden editar directamente")

    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Sin cambios para aplicar")

    place = await svc.update_place(place_id, data)
    if not place:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    return place


# ====================== DELETE (admin) ======================
@router.delete("/{place_id}", response_model=MessageResponse, summary="Eliminar local (admin)")
async def delete_place(
    place_id: UUID,
    current_user: dict = Depends(get_current_user),
    svc: SupabaseService = Depends(get_db_service),
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden eliminar")

    ok = await svc.delete_place(place_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    return MessageResponse(message="Local eliminado")
