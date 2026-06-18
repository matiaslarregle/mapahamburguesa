"""
Router del asistente IA con Gemini.
"""
import logging
from fastapi import APIRouter, Depends
from ..dependencies import get_db_service
from ..schemas import AssistantRequest, AssistantResponse
from ..services.supabase_service import SupabaseService
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_gemini(svc: SupabaseService) -> GeminiService:
    return GeminiService(svc)


@router.post(
    "/suggest",
    response_model=AssistantResponse,
    summary="Pedir sugerencias al asistente IA",
)
async def suggest(
    payload: AssistantRequest,
    svc: SupabaseService = Depends(get_db_service),
):
    gemini = get_gemini(svc)
    result = await gemini.suggest(
        user_message=payload.message,
        lat=payload.lat,
        lng=payload.lng,
        radius_km=payload.radius_km or 10.0,
    )
    return AssistantResponse(
        message=result["message"],
        suggested_places=result.get("suggested_places", []),
    )

