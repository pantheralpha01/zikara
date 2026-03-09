from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.profile import ComputerExperience, EducationLevel, EnglishLevel, IdType
from app.models.user import Gender


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    profile_pic_url: Optional[str] = None
    role: str
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    profile_pic_url: Optional[str] = None


class PartnerProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    business_name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    services_provided: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class PartnerUpdateRequest(BaseModel):
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    business_name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AgentProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    id_number: Optional[str] = None
    id_type: Optional[IdType] = None
    age: Optional[int] = None
    town: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    education_level: Optional[EducationLevel] = None
    english_level: Optional[EnglishLevel] = None
    computer_experience: Optional[ComputerExperience] = None
    have_a_computer: Optional[bool] = None
    access_to_internet: Optional[bool] = None
    internet_speed: Optional[str] = None
    description_of_self: Optional[str] = None
    total_bookings: int = 0
    total_refunds: int = 0
    total_disputes: int = 0
    avg_rating: float = 0.0
    hours_worked: float = 0.0
    quality_score: float = 0.0

    model_config = {"from_attributes": True}


class WalletOut(BaseModel):
    escrowBalance: float
    availableBalance: float
    pendingBalance: float


class CategoryAttributeSchema(BaseModel):
    name: str
    label: str
    type: str
    required: bool = True
    filterable: bool = True
    options: Optional[Any] = None


class CategoryCreate(BaseModel):
    name: str
    slug: str
    isActive: bool = True
    attributesSchema: List[CategoryAttributeSchema] = []


class CategoryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    display_order: int
    attributes_schema: List[Any] = []

    model_config = {"from_attributes": True}


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    isActive: Optional[bool] = None
    attributesSchema: Optional[List[Any]] = None


class ServiceCreate(BaseModel):
    categoryId: UUID
    name: str
    slug: str
    description: Optional[str] = None
    isActive: bool = True


class ServiceOut(BaseModel):
    id: UUID
    category_id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    display_order: int

    model_config = {"from_attributes": True}


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class ListingCreate(BaseModel):
    partnerId: UUID
    categoryId: UUID
    serviceId: Optional[UUID] = None
    title: str
    description: str
    city: str
    country: str
    priceFrom: float
    pricingType: str
    currency: str
    attributes: Optional[dict] = {}


class ListingOut(BaseModel):
    id: UUID
    partner_id: UUID
    category_id: UUID
    service_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    price_from: Optional[float] = None
    pricing_type: Optional[str] = None
    currency: Optional[str] = None
    attributes: Optional[dict] = {}
    status: str

    model_config = {"from_attributes": True}
