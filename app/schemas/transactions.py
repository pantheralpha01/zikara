from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr


class QuotePartner(BaseModel):
    partnerId: UUID
    serviceDescription: Optional[str] = None
    PartnerAmount: float = 0


class QuoteCreate(BaseModel):
    customerName: Optional[str] = None
    customerPhoneNumber: Optional[str] = None
    customerEmail: Optional[EmailStr] = None
    serviceTitle: Optional[str] = None
    referenceID: Optional[str] = None
    contractID: Optional[UUID] = None
    agentId: Optional[UUID] = None
    currency: str
    multiplepartnersEnabled: bool = False
    partners: List[QuotePartner] = []
    totalAmount: float
    paymentType: str
    costAtBooking: float = 0
    costPostEvent: float = 0
    payPostEventDueDate: Optional[datetime] = None
    serviceStartAt: Optional[datetime] = None
    serviceEndAt: Optional[datetime] = None
    serviceTimezone: Optional[str] = None


class QuoteOut(BaseModel):
    id: UUID
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    service_title: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    payment_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContractPartner(BaseModel):
    partnerId: UUID
    serviceDescription: Optional[str] = None
    PartnerAmount: float = 0


class ClientContractCreate(BaseModel):
    customerName: Optional[str] = None
    customerPhoneNumber: Optional[str] = None
    customerEmail: Optional[EmailStr] = None
    fileurl: Optional[str] = None
    serviceTitle: Optional[str] = None
    agentId: Optional[UUID] = None
    currency: Optional[str] = None
    partners: List[ContractPartner] = []
    totalAmount: float = 0
    paymentType: Optional[str] = None
    costAtBooking: float = 0
    costPostEvent: float = 0
    payPostEventDueDate: Optional[datetime] = None
    pickupLocation: Optional[str] = None
    destination: Optional[str] = None
    numberOfGuests: Optional[int] = None
    serviceStartAt: Optional[datetime] = None
    serviceEndAt: Optional[datetime] = None
    serviceTimezone: Optional[str] = None
    signedAt: Optional[datetime] = None


class ClientContractOut(BaseModel):
    id: UUID
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    service_title: Optional[str] = None
    total_amount: Optional[float] = None
    signed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClientContractUpdate(BaseModel):
    customer_name: Optional[str] = None
    file_url: Optional[str] = None
    signed_at: Optional[datetime] = None


class PartnerContractCreate(BaseModel):
    partnerID: UUID
    referenceID: str
    fileurl: str
    signedAt: datetime


class PartnerContractOut(BaseModel):
    id: UUID
    partner_id: UUID
    reference_id: Optional[str] = None
    file_url: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PartnerContractUpdate(BaseModel):
    reference_id: Optional[str] = None
    file_url: Optional[str] = None
    signed_at: Optional[datetime] = None


class AgentContractCreate(BaseModel):
    agentID: UUID
    referenceID: str
    fileurl: str
    signedAt: datetime


class AgentContractOut(BaseModel):
    id: UUID
    agent_id: UUID
    reference_id: Optional[str] = None
    file_url: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentContractUpdate(BaseModel):
    reference_id: Optional[str] = None
    file_url: Optional[str] = None
    signed_at: Optional[datetime] = None
