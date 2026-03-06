import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name = Column(String(255), nullable=True)
    customer_phone_number = Column(String(50), nullable=True)
    customer_email = Column(String(255), nullable=True)
    service_title = Column(String(500), nullable=True)
    reference_id = Column(String(255), nullable=True)
    contract_id = Column(UUID(as_uuid=True), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    currency = Column(String(10), nullable=True)
    multiple_partners_enabled = Column(String(5), default="false")
    partners = Column(JSON, default=list)
    total_amount = Column(Numeric(14, 2), nullable=True)
    payment_type = Column(String(50), nullable=True)
    cost_at_booking = Column(Numeric(14, 2), nullable=True)
    cost_post_event = Column(Numeric(14, 2), nullable=True)
    pay_post_event_due_date = Column(DateTime(timezone=True), nullable=True)
    service_start_at = Column(DateTime(timezone=True), nullable=True)
    service_end_at = Column(DateTime(timezone=True), nullable=True)
    service_timezone = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent = relationship("User", foreign_keys=[agent_id])
