"""
Configuración central de la aplicación.
Lee las variables de entorno desde .env usando pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------- Supabase (REQUERIDO) ----------
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # ---------- Google OAuth (configurado en Supabase Auth) ----------
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ---------- JWT ----------
    SECRET_KEY: str = "cambiar-en-produccion-usar-secrets-token"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días

    # ---------- DigitalOcean Spaces ----------
    DO_SPACES_KEY: str = ""
    DO_SPACES_SECRET: str = ""
    DO_SPACES_REGION: str = "nyc3"
    DO_SPACES_BUCKET: str = "mapahamburguesa"
    DO_SPACES_ENDPOINT: str = "https://nyc3.digitaloceanspaces.com"

    # ---------- Resend (emails) ----------
    RESEND_API_KEY: str = ""

    # ---------- Gemini (asistente IA) ----------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ---------- Cloudflare Turnstile ----------
    CF_TURNSTILE_SITE_KEY: str = ""
    CF_TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_FAIL_OPEN: bool = False  # en dev se puede pisar a true en .env


    # ---------- App ----------
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:5500"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5500",
        "https://mapahamburguesa.com",
        "https://www.mapahamburguesa.com",
    ]

    # ---------- Constantes de dominio ----------
    MAX_PHOTOS_PER_PLACE: int = 10
    MAX_IMAGE_WIDTH_PX: int = 1200
    DEFAULT_SEARCH_RADIUS_KM: float = 10.0
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


# Singleton: se importa como `from .config import settings`
settings = Settings()
