"""
Service layer: Supabase.
Centraliza queries comunes y aplica el shape de la API.
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from supabase import Client

from ..config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Wrapper de queries comunes a Supabase."""

    def __init__(self, client: Client):
        self.db = client

    # ====================== PROFILES ======================
    async def get_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Devuelve el profile o None si no existe."""
        try:
            res = (
                self.db.table("profiles")
                .select("*")
                .eq("id", str(user_id))
                .maybe_single()
                .execute()
            )
            return res.data
        except Exception as e:
            logger.error(f"Error get_profile({user_id}): {e}")
            return None

    async def get_user_email(self, user_id: UUID) -> Optional[str]:
        """Obtiene el email de un usuario desde auth.users (requiere service_role)."""
        try:
            res = self.db.auth.admin.get_user_by_id(str(user_id))
            return res.user.email if res and res.user else None
        except Exception as e:
            logger.error(f"Error get_user_email({user_id}): {e}")
            return None

    async def upsert_profile(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea o actualiza un profile (usado por callback OAuth)."""
        res = (
            self.db.table("profiles")
            .upsert({"id": str(user_id), **data}, on_conflict="id")
            .execute()
        )
        return res.data[0] if res.data else {}

    # ====================== PLACES ======================
    async def list_places(
        self,
        *,
        status: str = "approved",
        partido: Optional[str] = None,
        city: Optional[str] = None,
        place_type: Optional[str] = None,
        price_range: Optional[str] = None,
        has_delivery: Optional[bool] = None,
        payment_method: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Lista locales aplicando filtros encadenados.
        Siempre termina con limit/offset + order_by.
        """
        try:
            q = self.db.table("burger_places").select("*")
            q = q.eq("status", status)

            if partido:        q = q.eq("partido", partido)
            if city:           q = q.eq("city", city)
            if place_type:     q = q.eq("place_type", place_type)
            if price_range:    q = q.eq("price_range", price_range)
            if has_delivery is not None:
                q = q.eq("has_delivery", has_delivery)
            if payment_method:
                q = q.contains("payment_methods", [payment_method])

            q = q.order(order_by, desc=order_desc)
            q = q.range(offset, offset + limit - 1)

            res = q.execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error list_places: {e}", exc_info=True)
            return []

    async def count_places(
        self,
        *,
        status: str = "approved",
        partido: Optional[str] = None,
        city: Optional[str] = None,
        place_type: Optional[str] = None,
    ) -> int:
        """Cuenta locales (útil para paginación)."""
        try:
            q = self.db.table("burger_places").select("id", count="exact")
            q = q.eq("status", status)
            if partido:     q = q.eq("partido", partido)
            if city:        q = q.eq("city", city)
            if place_type:  q = q.eq("place_type", place_type)
            res = q.execute()
            return res.count or 0
        except Exception as e:
            logger.error(f"Error count_places: {e}")
            return 0

    async def search_nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda por proximidad usando earthdistance.
        Se ejecuta vía RPC (lo crearemos en la migración 0009).
        Fallback: traer todos y filtrar en Python si la RPC no existe.
        """
        try:
            res = self.db.rpc(
                "places_nearby",
                {
                    "p_lat": lat,
                    "p_lng": lng,
                    "p_radius_km": radius_km,
                    "p_limit": limit,
                },
            ).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"RPC places_nearby falló, usando fallback: {e}")
            return await self._fallback_nearby(lat, lng, radius_km, limit)

    async def _fallback_nearby(
        self, lat: float, lng: float, radius_km: float, limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback sin RPC — filtro en Python con fórmula haversine."""
        import math
        all_places = await self.list_places(limit=settings.MAX_PAGE_SIZE, offset=0)
        R = 6371.0  # radio Tierra en km

        def haversine(p):
            φ1, φ2 = math.radians(lat), math.radians(p["lat"])
            Δφ = math.radians(p["lat"] - lat)
            Δλ = math.radians(p["lng"] - lng)
            a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        nearby = [p for p in all_places if haversine(p) <= radius_km]
        nearby.sort(key=lambda p: haversine(p))
        return nearby[:limit]

    async def get_place(self, place_id: UUID) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self.db.table("burger_places")
                .select("*")
                .eq("id", str(place_id))
                .maybe_single()
                .execute()
            )
            return res.data
        except Exception as e:
            logger.error(f"Error get_place({place_id}): {e}")
            return None

    async def create_place(
        self, data: Dict[str, Any], added_by: UUID
    ) -> Dict[str, Any]:
        payload = {**data, "added_by": str(added_by), "status": "pending"}
        res = self.db.table("burger_places").insert(payload).execute()
        return res.data[0] if res.data else {}

    async def update_place(
        self, place_id: UUID, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        res = (
            self.db.table("burger_places")
            .update(data)
            .eq("id", str(place_id))
            .execute()
        )
        return res.data[0] if res.data else {}

    async def approve_place(
        self, place_id: UUID, approved_by: UUID
    ) -> Dict[str, Any]:
        from datetime import datetime
        res = (
            self.db.table("burger_places")
            .update(
                {
                    "status": "approved",
                    "approved_by": str(approved_by),
                    "approved_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("id", str(place_id))
            .execute()
        )
        return res.data[0] if res.data else {}

    async def reject_place(self, place_id: UUID) -> Dict[str, Any]:
        res = (
            self.db.table("burger_places")
            .update({"status": "rejected"})
            .eq("id", str(place_id))
            .execute()
        )
        return res.data[0] if res.data else {}

    async def delete_place(self, place_id: UUID) -> bool:
        res = (
            self.db.table("burger_places")
            .delete()
            .eq("id", str(place_id))
            .execute()
        )
        return bool(res.data)

    # ====================== REVIEWS ======================
    async def list_reviews(self, place_id: UUID) -> List[Dict[str, Any]]:
        res = (
            self.db.table("reviews")
            .select("*, profiles:user_id (name, avatar_url)")
            .eq("place_id", str(place_id))
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    async def get_user_review(
        self, place_id: UUID, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self.db.table("reviews")
                .select("*")
                .eq("place_id", str(place_id))
                .eq("user_id", str(user_id))
                .maybe_single()
                .execute()
            )
            return res.data if res else None
        except Exception:
            return None

    async def get_review(
        self, review_id: UUID
    ) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self.db.table("reviews")
                .select("*")
                .eq("id", str(review_id))
                .maybe_single()
                .execute()
            )
            return res.data if res else None
        except Exception as e:
            logger.error(f"Error get_review({review_id}): {e}")
            return None

    async def create_review(
        self, place_id: UUID, user_id: UUID, rating: int, comment: Optional[str]
    ) -> Dict[str, Any]:
        res = (
            self.db.table("reviews")
            .insert(
                {
                    "place_id": str(place_id),
                    "user_id": str(user_id),
                    "rating": rating,
                    "comment": comment,
                }
            )
            .execute()
        )
        return res.data[0] if res.data else {}

    async def update_review(
        self, review_id: UUID, rating: int, comment: Optional[str]
    ) -> Dict[str, Any]:
        res = (
            self.db.table("reviews")
            .update({"rating": rating, "comment": comment})
            .eq("id", str(review_id))
            .execute()
        )
        return res.data[0] if res.data else {}

    async def delete_review(self, review_id: UUID) -> bool:
        res = self.db.table("reviews").delete().eq("id", str(review_id)).execute()
        return bool(res.data)

    # ====================== PHOTOS ======================
    async def list_photos(self, place_id: UUID) -> List[Dict[str, Any]]:
        res = (
            self.db.table("photos")
            .select("*")
            .eq("place_id", str(place_id))
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []

    async def count_photos(self, place_id: UUID) -> int:
        res = (
            self.db.table("photos")
            .select("id", count="exact")
            .eq("place_id", str(place_id))
            .execute()
        )
        return res.count or 0

    async def create_photo(
        self, place_id: UUID, user_id: UUID, url: str, is_cover: bool = False, review_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        res = (
            self.db.table("photos")
            .insert(
                {
                    "place_id": str(place_id),
                    "user_id": str(user_id),
                    "url": url,
                    "is_cover": is_cover,
                    "review_id": str(review_id) if review_id else None,  # ← YA ESTÁ, solo verifica
                }
            )
            .execute()
        )
        return res.data[0] if res.data else {}

    async def delete_photo(self, photo_id: UUID) -> bool:
        res = self.db.table("photos").delete().eq("id", str(photo_id)).execute()
        return bool(res.data)

    async def set_cover_photo(self, place_id: UUID, photo_id: UUID) -> Dict[str, Any]:
        """Una sola portada por local: desmarcamos las demás y marcamos la nueva."""
        # 1) Desmarcar todas
        self.db.table("photos").update({"is_cover": False}).eq(
            "place_id", str(place_id)
        ).execute()
        # 2) Marcar la nueva
        res = (
            self.db.table("photos")
            .update({"is_cover": True})
            .eq("id", str(photo_id))
            .eq("place_id", str(place_id))
            .execute()
        )
        return res.data[0] if res.data else {}

    # ====================== SUGGESTIONS ======================
    async def list_pending_suggestions(self) -> List[Dict[str, Any]]:
        res = (
            self.db.table("edit_suggestions")
            .select("*, profiles:suggested_by (name), places:place_id (name)")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []

    async def create_suggestion(
        self,
        place_id: UUID,
        suggested_by: UUID,
        field_name: str,
        old_value: Optional[str],
        new_value: str,
    ) -> Dict[str, Any]:
        res = (
            self.db.table("edit_suggestions")
            .insert(
                {
                    "place_id": str(place_id),
                    "suggested_by": str(suggested_by),
                    "field_name": field_name,
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )
            .execute()
        )
        return res.data[0] if res.data else {}

    async def resolve_suggestion(
        self,
        suggestion_id: UUID,
        approved: bool,
        reviewed_by: UUID,
    ) -> Dict[str, Any]:
        from datetime import datetime
        status = "approved" if approved else "rejected"
        res = (
            self.db.table("edit_suggestions")
            .update(
                {
                    "status": status,
                    "reviewed_by": str(reviewed_by),
                    "reviewed_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("id", str(suggestion_id))
            .execute()
        )
        return res.data[0] if res.data else {}

    # ====================== ADMIN STATS ======================
    async def admin_stats(self) -> Dict[str, int]:
        """Conteos globales para el dashboard admin."""
        try:
            places_pending = (
                self.db.table("burger_places")
                .select("id", count="exact")
                .eq("status", "pending")
                .execute()
            ).count or 0
            places_approved = (
                self.db.table("burger_places")
                .select("id", count="exact")
                .eq("status", "approved")
                .execute()
            ).count or 0
            suggestions_pending = (
                self.db.table("edit_suggestions")
                .select("id", count="exact")
                .eq("status", "pending")
                .execute()
            ).count or 0
            users_total = (
                self.db.table("profiles").select("id", count="exact").execute()
            ).count or 0
            return {
                "places_pending": places_pending,
                "places_approved": places_approved,
                "suggestions_pending": suggestions_pending,
                "users_total": users_total,
            }
        except Exception as e:
            logger.error(f"Error admin_stats: {e}")
            return {}


# Función helper para usar como dependencia
def get_supabase_service(client: Client = None) -> SupabaseService:
    from ..database import get_supabase_admin
    return SupabaseService(client or get_supabase_admin())
