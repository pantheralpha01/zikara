from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class BookingPartner(BaseModel):
    partnerId: UUID
    amount: float = 0


class BookingCreate(BaseModel):
    clientId: UUID
    agentId: UUID
    contractId: Optional[UUID] = None
    paymentId: Optional[UUID] = None
    currency: str
    partners: List[BookingPartner] = []
    totalAmount: float
    paymentType: str
    costAtBooking: float = 0
    costPostEvent: float = 0
    dueDate: Optional[datetime] = None
    serviceStartAt: Optional[datetime] = None
    serviceEndAt: Optional[datetime] = None
    status: str = "confirmed"


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class BookingOut(BaseModel):
    id: UUID
    client_id: UUID
    agent_id: UUID
    contract_id: Optional[UUID] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_type: Optional[str] = None
    amount_paid: float = 0
    payment_status: str = "unpaid"
    status: str
    service_start_at: Optional[datetime] = None
    service_end_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaymentInitiate(BaseModel):
    bookingId: UUID
    amount: float
    currency: str
    provider: str


class PaymentConfirm(BaseModel):
    providerReference: Optional[str] = None


class PaymentOut(BaseModel):
    id: UUID
    booking_id: Optional[UUID] = None
    amount: float
    currency: str
    provider: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WithdrawRequest(BaseModel):
    amount: float


class RefundCreate(BaseModel):
    bookingId: UUID
    amount: float
    reason: str


class RefundUpdate(BaseModel):
    status: Optional[str] = None


class RefundOut(BaseModel):
    id: UUID
    booking_id: UUID
    amount: float
    reason: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DisputeCreate(BaseModel):
    bookingId: UUID
    reason: str
    description: str


class DisputeUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None


class DisputeOut(BaseModel):
    id: UUID
    booking_id: UUID
    reason: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    rating: int
    comment: str


class ReviewOut(BaseModel):
    id: UUID
    booking_id: UUID
    reviewer_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
