from typing import Any, List, Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, model_validator


class BookingPartner(BaseModel):
    partnerId: UUID
    amount: float = 0


class BookingCreate(BaseModel):
    clientId: UUID
    agentId: UUID
    contractId: Optional[UUID] = None
    chakraEnquiryId: Optional[str] = None
    currency: str
    partners: List[BookingPartner] = []
    totalAmount: float
    paymentType: Literal["full", "partial"]
    costAtBooking: float = 0
    costPostEvent: float = 0
    numberOfAdults: int = 0
    numberOfChildren: int = 0
    numberOfInfants: int = 0
    residency: Optional[Literal["CITIZEN", "RESIDENT", "NON-RESIDENT"] ] = None
    pets: bool = False
    pickupLocation: Optional[str] = None
    destinationLocation: Optional[str] = None
    specialNotes: Optional[str] = None
    dueDate: Optional[datetime] = None
    serviceStartAt: Optional[datetime] = None
    serviceEndAt: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_partial_payment(self):
        if self.paymentType == "partial":
            expected = round(self.costAtBooking + self.costPostEvent, 2)
            if abs(self.totalAmount - expected) > 0.01:
                raise ValueError(
                    f"For partial payment, totalAmount ({self.totalAmount}) must equal "
                    f"costAtBooking ({self.costAtBooking}) + costPostEvent ({self.costPostEvent})"
                )
        return self


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    number_of_adults: Optional[int] = None
    number_of_children: Optional[int] = None
    number_of_infants: Optional[int] = None
    residency: Optional[Literal["CITIZEN", "RESIDENT", "NON-RESIDENT"] ] = None
    pets: Optional[bool] = None
    pickup_location: Optional[str] = None
    destination_location: Optional[str] = None
    special_notes: Optional[str] = None


class BookingReassign(BaseModel):
    agentId: UUID


class BookingOut(BaseModel):
    id: UUID
    client_id: UUID
    agent_id: UUID
    contract_id: Optional[UUID] = None
    chakra_enquiry_id: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_type: Optional[Literal["full", "partial"]] = None
    amount_paid: float = 0
    payment_status: Literal["unpaid", "partially_paid", "fully_paid"] = "unpaid"
    number_of_adults: int = 0
    number_of_children: int = 0
    number_of_infants: int = 0
    total_guests: int = 0
    residency: Optional[Literal["CITIZEN", "RESIDENT", "NON-RESIDENT"] ] = None
    pets: bool = False
    pickup_location: Optional[str] = None
    destination_location: Optional[str] = None
    special_notes: Optional[str] = None
    status: Literal["confirmed", "completed", "cancelled", "pending"]
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
    reference_id: Optional[str] = None


class RefundUpdate(BaseModel):
    status: Optional[str] = None
    reference_id: Optional[str] = None


class RefundOut(BaseModel):
    id: UUID
    booking_id: UUID
    client_id: UUID
    amount: float
    reason: Optional[str] = None
    reference_id: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DisputeCreate(BaseModel):
    bookingId: UUID
    reason: str
    description: str
    reference_id: Optional[str] = None


class DisputeUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    reference_id: Optional[str] = None


class DisputeOut(BaseModel):
    id: UUID
    booking_id: UUID
    client_id: UUID
    reason: Optional[str] = None
    description: Optional[str] = None
    reference_id: Optional[str] = None
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
