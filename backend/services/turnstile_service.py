"""
Service layer: Cloudflare Turnstile (verificación server-side).
Documentación: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
"""
import logging
import httpx
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileService:
    """Verifica tokens de Turnstile contra el endpoint de Cloudflare."""

    def __init__(self):
        self.secret_key = settings.CF_TURNSTILE_SECRET_KEY
        self.enabled = bool(self.secret_key)

    async def verify(
        self,
        token: str,
        *,
        remote_ip: Optional[str] = None,
    ) -> bool:
        """
        Verifica un token con Cloudflare.
        Devuelve True si el token es válido.
        En desarrollo (sin secret key), permite pasar (fail-open)
        SOLO si TURNSTILE_FAIL_OPEN=true en .env.
        """
        # ---------- Modo desarrollo ----------
        if not self.enabled:
            if settings.TURNSTILE_FAIL_OPEN:
                logger.warning(
                    "TURNSTILE deshabilitado (sin secret key) — fail-open activado"
                )
                return True
            logger.warning("TURNSTILE deshabilitado — token no verificado")
            return False

        # ---------- Sin token ----------
        if not token:
            logger.warning("Turnstile: token vacío")
            return False

        # ---------- Verificación ----------
        try:
            payload = {"secret": self.secret_key, "response": token}
            if remote_ip:
                payload["remoteip"] = remote_ip

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(VERIFY_URL, data=payload)

            if resp.status_code != 200:
                logger.error(f"Turnstile HTTP {resp.status_code}: {resp.text}")
                return False

            data = resp.json()
            success = bool(data.get("success"))
            if not success:
                logger.warning(f"Turnstile rejected: {data.get('error-codes', [])}")
            return success

        except httpx.TimeoutException:
            logger.error("Turnstile: timeout al verificar")
            return False
        except Exception as e:
            logger.error(f"Turnstile: error inesperado: {e}", exc_info=True)
            return False


def get_turnstile_service() -> TurnstileService:
    return TurnstileService()
