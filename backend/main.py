"""
Entry point de MapaHamburguesa API.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth, places, reviews, photos, suggestions, admin, assistant

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO if settings.is_development else logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("mapahamburguesa")


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 MapaHamburguesa arrancando — env={settings.ENVIRONMENT}")
    yield
    logger.info("👋 MapaHamburguesa cerrando")


# ---------- App ----------
app = FastAPI(
    title="MapaHamburguesa API",
    description="API para mapear hamburgueserías en la Provincia de Buenos Aires",
    version="1.0.0",
    lifespan=lifespan,
    # En producción, ocultamos docs para evitar exponer la API
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
app.include_router(auth.router,      prefix="/auth",      tags=["Auth"])
app.include_router(places.router,    prefix="/places",    tags=["Places"])
app.include_router(reviews.router,   prefix="/places",    tags=["Reviews"])
app.include_router(photos.router,    prefix="/places",    tags=["Photos"])
app.include_router(suggestions.router, prefix="/places",  tags=["Suggestions"])
app.include_router(admin.router,     prefix="/admin",     tags=["Admin"])
app.include_router(assistant.router, prefix="/assistant", tags=["Assistant"])


# ---------- Health ----------
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": "MapaHamburguesa API",
        "version": "1.0.0",
        "env": settings.ENVIRONMENT,
        "status": "ok",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
