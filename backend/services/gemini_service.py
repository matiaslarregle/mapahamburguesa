"""
Service layer: Asistente IA con Gemini.
Recibe mensaje del usuario → busca candidatos en Supabase → redacta respuesta conversacional.
"""
import logging
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from ..config import settings
from .supabase_service import SupabaseService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Sos un asistente amigable y conciso de "MapaHamburguesa", una app que ayuda a los usuarios
a encontrar hamburgueserías en la Provincia de Buenos Aires, Argentina.

Tu objetivo:
- Ayudar al usuario a elegir un local basándote en sus preferencias (sabor, presupuesto, tipo, zona).
- Recomendar locales de la lista provista (no inventes locales que no estén en la lista).
- Si la lista está vacía, decí amablemente que no encontramos locales que coincidan y sugerí relajar filtros.
- Usá un tono cálido, argentino, con un toque de humor. Emojis bienvenidos pero sin abusar.
- Respondé SIEMPRE en español rioplatense.
- Sé breve: máximo 3-4 líneas + la lista de locales sugeridos.

Formato de salida (JSON estricto, sin texto fuera del JSON):
{
  "message": "texto conversacional para el usuario",
  "suggested_place_ids": ["uuid1", "uuid2", "..."]
}
"""


class GeminiService:
    """Asistente de onboarding / recomendación."""

    def __init__(self, supabase_service: SupabaseService):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL) if settings.GEMINI_API_KEY else None
        self.supabase = supabase_service

    async def suggest(
        self,
        user_message: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_km: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Pipeline:
        1) Recuperar candidatos (cercanos si hay coords, sino últimos aprobados).
        2) Armar contexto con hasta 10 locales.
        3) Pedirle a Gemini que elija y redacte.
        4) Devolver mensaje + lista de IDs sugeridos.
        """
        # ---------- 1) Candidatos ----------
        if lat is not None and lng is not None:
            candidates = await self.supabase.search_nearby(
                lat=lat, lng=lng, radius_km=radius_km, limit=15
            )
        else:
            candidates = await self.supabase.list_places(
                status="approved", limit=15, offset=0,
                order_by="avg_rating", order_desc=True,
            )

        # ---------- 2) Fallback sin Gemini ----------
        if not self.model or not settings.GEMINI_API_KEY:
            return self._fallback_response(user_message, candidates)

        # ---------- 3) Prompt ----------
        candidates_brief = [
            {
                "id": c["id"],
                "name": c["name"],
                "partido": c.get("partido"),
                "city": c.get("city"),
                "place_type": c.get("place_type"),
                "price_range": c.get("price_range"),
                "avg_rating": c.get("avg_rating", 0),
                "has_delivery": c.get("has_delivery", False),
            }
            for c in candidates
        ]

        user_prompt = f"""
Mensaje del usuario: "{user_message}"

Locales disponibles (elige los más relevantes para su pedido):
{json.dumps(candidates_brief, ensure_ascii=False, indent=2)}

Devolvé SOLO el JSON con 'message' y 'suggested_place_ids' (los IDs de la lista de arriba).
Si ninguno encaja, devolvé suggested_place_ids: [] y un message explicando por qué.
"""

        # ---------- 4) Llamada a Gemini ----------
        try:
            response = self.model.generate_content(
                [SYSTEM_PROMPT, user_prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                    response_mime_type="application/json",  # fuerza JSON
                ),
            )
            raw = response.text.strip()

            # Gemini a veces envuelve el JSON en ```json ... ```
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            message = parsed.get("message", "Acá van algunas opciones para vos:")
            suggested_ids = parsed.get("suggested_place_ids", [])

            # Hidratar los lugares sugeridos con datos completos
            suggested_places = [
                c for c in candidates if c["id"] in suggested_ids
            ][:5]

            return {"message": message, "suggested_places": suggested_places}

        except json.JSONDecodeError as e:
            logger.error(f"Gemini devolvió JSON inválido: {e} | raw={raw[:200]}")
            return self._fallback_response(user_message, candidates)
        except Exception as e:
            logger.error(f"Error llamando a Gemini: {e}", exc_info=True)
            return self._fallback_response(user_message, candidates)

    def _fallback_response(
        self, user_message: str, candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Si Gemini no está disponible, devolvemos los top por rating."""
        top = sorted(candidates, key=lambda c: c.get("avg_rating") or 0, reverse=True)[:5]
        msg = (
            "Estas son nuestras mejores recomendaciones:" if top
            else "Por ahora no encontramos locales que coincidan con tu búsqueda. Probá relajar algún filtro."
        )
        return {"message": msg, "suggested_places": top}


def get_gemini_service(supabase_service: SupabaseService) -> GeminiService:
    return GeminiService(supabase_service)
