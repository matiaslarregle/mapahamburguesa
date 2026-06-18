"""
Service layer: Resend para emails transaccionales.
"""
import logging
import resend
from typing import Optional, List
from ..config import settings

logger = logging.getLogger(__name__)

# Inicializar API key una sola vez
if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY

FROM_ADDRESS = "MapaHamburguesa <noreply@mapahamburguesa.com>"


class EmailService:
    """Envía emails transaccionales."""

    @staticmethod
    async def send_email(
        to: str | List[str],
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> bool:
        """
        Envía un email vía Resend.
        Devuelve True si el envío fue aceptado por Resend.
        """
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY no configurada — email no enviado")
            logger.info(f"[MOCK EMAIL] To: {to} | Subject: {subject}")
            return False

        try:
            params = {
                "from": FROM_ADDRESS,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "html": html,
            }
            if text:
                params["text"] = text

            resend.Emails.send(params)
            logger.info(f"Email enviado a {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Error enviando email a {to}: {e}", exc_info=True)
            return False

    # ====================== Plantillas ======================
    @staticmethod
    def template_place_approved(place_name: str, place_url: str) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #e85d04;">🍔 ¡Tu local fue aprobado!</h1>
            <p>Hola,</p>
            <p>Buenas noticias: el local <strong>{place_name}</strong> que sugeriste ya está visible en MapaHamburguesa.</p>
            <p>Gracias por contribuir al mapa. 🥳</p>
            <p style="margin: 30px 0;">
                <a href="{place_url}" style="background: #e85d04; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                    Ver local en el mapa
                </a>
            </p>
            <p style="color: #666; font-size: 12px;">— El equipo de MapaHamburguesa</p>
        </div>
        """

    @staticmethod
    def template_place_rejected(place_name: str, reason: str = "") -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #999;">Sobre tu sugerencia: {place_name}</h1>
            <p>Hola,</p>
            <p>Revisamos el local <strong>{place_name}</strong> que sugeriste y no pudimos aprobarlo en esta ocasión.</p>
            {f'<p><strong>Motivo:</strong> {reason}</p>' if reason else ''}
            <p>Si creés que es un error, podés volver a sugerirlo con información más completa.</p>
            <p style="color: #666; font-size: 12px;">— El equipo de MapaHamburguesa</p>
        </div>
        """

    @staticmethod
    def template_suggestion_approved(place_name: str, field_name: str) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #2a9d8f;">✅ ¡Tu sugerencia fue aceptada!</h1>
            <p>El campo <strong>{field_name}</strong> del local <strong>{place_name}</strong> se actualizó con tu aporte.</p>
            <p>Gracias por ayudar a mejorar la información del mapa. 🙌</p>
        </div>
        """


def get_email_service() -> EmailService:
    return EmailService()
