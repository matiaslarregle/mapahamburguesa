"""
Modelos Pydantic (request/response) de la API.
Mantenemos la paridad 1:1 con el schema de Supabase.
"""
from datetime import datetime
from typing import Optional, List, Dict, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ====================== Enums / Literals ======================
PriceRange   = Literal["cheap", "mid", "expensive"]
PlaceType    = Literal["fast_food", "gourmet", "dark_kitchen", "food_truck", "other"]
PlaceStatus  = Literal["pending", "approved", "rejected"]
PaymentMethod = Literal["efectivo", "debito", "credito", "mp", "uala", "transferencia"]
UserRole     = Literal["user", "moderator", "admin"]
DayKey       = Literal["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


# ====================== Auth / Profile ======================
class UserProfile(BaseModel):
    id: UUID
    name: str
    avatar_url: Optional[str] = None
    role: UserRole = "user"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class AuthMeResponse(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: Optional[str] = None
    role: UserRole
    is_active: bool


# ====================== Places ======================
class PlaceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    address: str = Field(..., min_length=5)
    city: str = Field(..., max_length=100)
    partido: str = Field(..., max_length=100)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = None
    instagram: Optional[str] = Field(None, max_length=100)
    facebook: Optional[str] = Field(None, max_length=100)
    price_range: Optional[PriceRange] = "mid"
    place_type: Optional[PlaceType] = "other"
    has_delivery: bool = False
    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    schedule: Optional[Dict[DayKey, Optional[str]]] = None
    menu_highlights: Optional[str] = None


class PlaceCreate(PlaceBase):
    pass


class PlaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = None
    partido: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    price_range: Optional[PriceRange] = None
    place_type: Optional[PlaceType] = None
    has_delivery: Optional[bool] = None
    payment_methods: Optional[List[PaymentMethod]] = None
    schedule: Optional[Dict[DayKey, Optional[str]]] = None
    menu_highlights: Optional[str] = None


class PlaceResponse(PlaceBase):
    id: UUID
    status: PlaceStatus
    avg_rating: float = 0
    review_count: int = 0
    added_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("avg_rating", mode="before")
    @classmethod
    def default_avg_rating(cls, v):
        # Locales sin reviews todavía vienen con avg_rating=None desde la DB
        return 0 if v is None else v

    class Config:
        from_attributes = True


class PlaceListResponse(BaseModel):
    items: List[PlaceResponse]
    total: int
    limit: int
    offset: int


# ====================== Reviews ======================
class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: UUID
    place_id: UUID
    user_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReviewWithUser(ReviewResponse):
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None


# ====================== Photos ======================
class PhotoResponse(BaseModel):
    id: UUID
    place_id: UUID
    user_id: UUID
    url: str
    is_cover: bool
    review_id: Optional[UUID] = None  # ← AGREGÁ ESTA LÍNEA
    created_at: datetime


# ====================== Suggestions ======================
class SuggestionCreate(BaseModel):
    field_name: str = Field(..., max_length=100)
    new_value: str = Field(..., min_length=1, max_length=2000)


class SuggestionResponse(BaseModel):
    id: UUID
    place_id: UUID
    suggested_by: UUID
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


# ====================== Assistant (Gemini) ======================
class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=1000)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(10.0, gt=0, le=100)


class AssistantPlaceSuggestion(BaseModel):
    id: UUID
    name: str
    address: str
    partido: str
    avg_rating: float = 0
    price_range: Optional[PriceRange] = None
    place_type: Optional[PlaceType] = None

    @field_validator("avg_rating", mode="before")
    @classmethod
    def default_avg_rating(cls, v):
        return 0 if v is None else v


class AssistantResponse(BaseModel):
    message: str
    suggested_places: List[AssistantPlaceSuggestion] = []


# ====================== Genéricos ======================
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
