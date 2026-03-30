from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr


class EnquiryCreateRequest(BaseModel):
    """Sent by Chakra HQ when a new enquiry arrives."""
    chakra_enquiry_id: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class EnquiryOut(BaseModel):
    id: UUID
    chakra_enquiry_id: Optional[str] = None
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    status: str
    title: Optional[str] = None
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EnquiryAssignResponse(BaseModel):
    enquiry: EnquiryOut
    assigned: bool
    message: str
