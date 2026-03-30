import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, JSON, Integer, Numeric, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("client_contracts.id"), nullable=True)
    payment_id = Column(UUID(as_uuid=True), nullable=True)
    chakra_enquiry_id = Column(String(255), nullable=True, index=True)
    currency = Column(String(10), nullable=True)
    partners = Column(JSON, default=list)
    total_amount = Column(Numeric(14, 2), nullable=True)
    payment_type = Column(String(50), nullable=True)
    cost_at_booking = Column(Numeric(14, 2), nullable=True)
    cost_post_event = Column(Numeric(14, 2), nullable=True)
    number_of_adults = Column(Integer, default=0, nullable=False)
    number_of_children = Column(Integer, default=0, nullable=False)
    number_of_infants = Column(Integer, default=0, nullable=False)
    residency = Column(
        Enum("CITIZEN", "RESIDENT", "NON-RESIDENT", name="booking_residency"),
        nullable=True,
    )
    pets = Column(Boolean, default=False, nullable=False)
    pickup_location = Column(String(255), nullable=True)
    destination_location = Column(String(255), nullable=True)
    special_notes = Column(String(1000), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    service_start_at = Column(DateTime(timezone=True), nullable=True)
    service_end_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum("confirmed", "completed", "cancelled", "pending", name="booking_status"),
        default="confirmed",
        nullable=False,
    )
    amount_paid = Column(Numeric(14, 2), default=0, nullable=False)
    payment_status = Column(
        Enum("unpaid", "partially_paid", "fully_paid", name="booking_payment_status"),
        default="unpaid",
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def total_guests(self) -> int:
        return int((self.number_of_adults or 0) + (self.number_of_children or 0) + (self.number_of_infants or 0))

    client = relationship("User", foreign_keys=[client_id])
    agent = relationship("User", foreign_keys=[agent_id])
    contract = relationship("ClientContract")
    reviews = relationship("Review", back_populates="booking")
    booking_partners = relationship("BookingPartner", back_populates="booking", cascade="all, delete-orphan")


class BookingPartner(Base):
    """Normalised per-partner allocation for a booking.
    Created alongside bookings.partners (JSON) for queryable partner stats.
    """
    __tablename__ = "booking_partners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    partner_id = Column(
        UUID(as_uuid=True), ForeignKey("partner_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount = Column(Numeric(14, 2), default=0, nullable=False)

    booking = relationship("Booking", back_populates="booking_partners")
    partner = relationship("PartnerProfile")
