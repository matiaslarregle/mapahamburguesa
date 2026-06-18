"""
Service layer: Supabase Storage para fotos de locales.
"""
import logging
import io
import uuid
from typing import Optional, Tuple
from uuid import UUID
from PIL import Image
from supabase import Client

from ..config import settings

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg":  "jpg",
    "image/png":  "png",
    "image/webp": "webp",
}
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB (antes de resize)


class StorageService:
    """Sube y borra fotos en Supabase Storage."""

    BUCKET = "place-photos"

    def __init__(self, client: Client):
        self.client = client
        self.storage = client.storage

    # ====================== Validaciones ======================
    @staticmethod
    def validate_image(content: bytes, content_type: Optional[str]) -> Tuple[bool, str]:
        """
        Valida tipo MIME y tamaño ANTES de procesar.
        Devuelve (ok, mensaje_error).
        """
        if not content:
            return False, "Archivo vacío"

        if len(content) > MAX_FILE_SIZE_BYTES:
            return False, f"Archivo muy grande (máx {MAX_FILE_SIZE_BYTES // (1024*1024)} MB)"

        ct = (content_type or "").lower()
        if ct not in ALLOWED_MIME_TYPES:
            return False, f"Tipo de archivo no permitido: {content_type}"

        try:
            img = Image.open(io.BytesIO(content))
            img.verify()  # valida que sea imagen real
        except Exception as e:
            return False, f"Archivo no es una imagen válida: {str(e)}"

        return True, ""

    @staticmethod
    def resize_image(
        content: bytes, max_width: int = None
    ) -> Tuple[bytes, str]:
        """
        Redimensiona la imagen a max_width (default config) y la devuelve como JPEG.
        Retorna (bytes, content_type).
        """
        max_width = max_width or settings.MAX_IMAGE_WIDTH_PX

        img = Image.open(io.BytesIO(content))

        # Convertir paletas/modos raros a RGB
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Solo redimensionar si es más grande
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue(), "image/jpeg"

    # ====================== Upload ======================
    async def upload_photo(
        self,
        place_id: UUID,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Sube una foto al bucket. Path: {place_id}/{uuid}.jpg
        Devuelve la URL pública.
        """
        # 1) Validar
        ok, err = self.validate_image(file_content, content_type)
        if not ok:
            raise ValueError(err)

        # 2) Resize (best-effort — si falla, sube el original)
        try:
            resized_bytes, _ = self.resize_image(file_content)
        except Exception as e:
            logger.warning(f"No se pudo redimensionar la imagen, subiendo original: {e}")
            resized_bytes = file_content

        # 3) Path
        file_id = uuid.uuid4()
        path = f"{place_id}/{file_id}.jpg"

        # 4) Upload
        self.storage.from_(self.BUCKET).upload(
            path=path,
            file=resized_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "false"},
        )

        # 5) URL pública
        public_url = self.storage.from_(self.BUCKET).get_public_url(path)
        return public_url

    # ====================== Delete ======================
    async def delete_photo(self, url: str) -> bool:
        """
        Borra una foto a partir de su URL pública.
        Extrae el path del bucket y llama a remove().
        """
        try:
            marker = f"/{self.BUCKET}/"
            if marker not in url:
                logger.warning(f"URL no pertenece al bucket {self.BUCKET}: {url}")
                return False

            path = url.split(marker, 1)[1]
            self.storage.from_(self.BUCKET).remove([path])
            return True
        except Exception as e:
            logger.error(f"Error borrando foto {url}: {e}")
            return False


def get_storage_service(client: Client = None) -> StorageService:
    from ..database import get_supabase_admin
    return StorageService(client or get_supabase_admin())
