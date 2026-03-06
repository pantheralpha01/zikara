import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    provider = Column(String(100), nullable=True)
    provider_reference = Column(String(500), nullable=True)
    status = Column(
        Enum("pending", "success", "failed", name="payment_status"),
        default="pending",
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    booking = relationship("Booking")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    escrow_balance = Column(Numeric(14, 2), default=0, nullable=False)
    available_balance = Column(Numeric(14, 2), default=0, nullable=False)
    pending_balance = Column(Numeric(14, 2), default=0, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    partner = relationship("PartnerProfile", back_populates="wallet")
