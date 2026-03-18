import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey,
    Integer, Numeric, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class PlatformStats(Base):
    __tablename__ = "platform_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, unique=True, index=True)

    # Users
    total_customers = Column(Integer, default=0, nullable=False)
    total_agents = Column(Integer, default=0, nullable=False)
    total_partners = Column(Integer, default=0, nullable=False)
    new_customers = Column(Integer, default=0, nullable=False)
    new_agents = Column(Integer, default=0, nullable=False)
    new_partners = Column(Integer, default=0, nullable=False)

    # Bookings lifecycle
    bookings_created = Column(Integer, default=0, nullable=False)
    bookings_confirmed = Column(Integer, default=0, nullable=False)
    ongoing_bookings = Column(Integer, default=0, nullable=False)
    bookings_completed = Column(Integer, default=0, nullable=False)
    bookings_cancelled = Column(Integer, default=0, nullable=False)

    # Financial
    gross_booking_value = Column(Numeric(15, 2), default=0, nullable=False)
    platform_revenue = Column(Numeric(15, 2), default=0, nullable=False)
    partner_payouts = Column(Numeric(15, 2), default=0, nullable=False)
    refunds_issued = Column(Numeric(15, 2), default=0, nullable=False)

    # Escrow
    escrow_balance = Column(Numeric(15, 2), default=0, nullable=False)
    escrow_funds_held = Column(Numeric(15, 2), default=0, nullable=False)
    escrow_funds_released = Column(Numeric(15, 2), default=0, nullable=False)
    escrow_pending_release = Column(Numeric(15, 2), default=0, nullable=False)

    # Operations
    disputes_opened = Column(Integer, default=0, nullable=False)
    disputes_closed = Column(Integer, default=0, nullable=False)

    # Reviews
    total_reviews = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AgentStats(Base):
    __tablename__ = "agent_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    total_bookings = Column(Integer, default=0, nullable=False)
    ongoing_bookings = Column(Integer, default=0, nullable=False)
    completed_bookings = Column(Integer, default=0, nullable=False)
    cancelled_bookings = Column(Integer, default=0, nullable=False)

    total_refunds = Column(Integer, default=0, nullable=False)
    total_disputes = Column(Integer, default=0, nullable=False)

    review_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)
    five_star_rate = Column(Float, default=0.0, nullable=False)

    hours_worked = Column(Float, default=0.0, nullable=False)

    refund_rate = Column(Float, default=0.0, nullable=False)
    dispute_rate = Column(Float, default=0.0, nullable=False)
    booking_efficiency = Column(Float, default=0.0, nullable=False)
    quality_score = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("agent_id", "month", "year", name="uq_agent_stats_month"),)


class AgentDailyStats(Base):
    __tablename__ = "agent_daily_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)

    bookings_handled = Column(Integer, default=0, nullable=False)
    ongoing_bookings = Column(Integer, default=0, nullable=False)
    completed_bookings = Column(Integer, default=0, nullable=False)
    refunds_handled = Column(Integer, default=0, nullable=False)
    disputes_handled = Column(Integer, default=0, nullable=False)
    hours_worked = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("agent_id", "date", name="uq_agent_daily_stats"),)


class PartnerStats(Base):
    __tablename__ = "partner_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("partner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    bookings_received = Column(Integer, default=0, nullable=False)
    ongoing_bookings = Column(Integer, default=0, nullable=False)
    bookings_completed = Column(Integer, default=0, nullable=False)
    bookings_cancelled = Column(Integer, default=0, nullable=False)

    revenue_generated = Column(Numeric(12, 2), default=0, nullable=False)
    payouts_received = Column(Numeric(12, 2), default=0, nullable=False)
    pending_payouts = Column(Numeric(12, 2), default=0, nullable=False)

    review_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("partner_id", "month", "year", name="uq_partner_stats_month"),)


class PartnerDailyStats(Base):
    __tablename__ = "partner_daily_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("partner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False)

    bookings_received = Column(Integer, default=0, nullable=False)
    ongoing_bookings = Column(Integer, default=0, nullable=False)
    bookings_completed = Column(Integer, default=0, nullable=False)
    revenue_generated = Column(Numeric(12, 2), default=0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("partner_id", "date", name="uq_partner_daily_stats"),)
