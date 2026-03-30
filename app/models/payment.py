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
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_profiles.id", ondelete="CASCADE"), unique=True, nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.id", ondelete="CASCADE"), unique=True, nullable=True)
    escrow_balance = Column(Numeric(14, 2), default=0, nullable=False)
    available_balance = Column(Numeric(14, 2), default=0, nullable=False)
    pending_balance = Column(Numeric(14, 2), default=0, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    partner = relationship("PartnerProfile", back_populates="wallet")
    agent = relationship("AgentProfile", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    """Immutable log of every amount that moved in/out of a wallet."""
    __tablename__ = "wallet_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = Column(
        Enum("escrow_in", "escrow_release", "payout", "refund_debit", name="wallet_tx_type"),
        nullable=False,
    )
    amount = Column(Numeric(14, 2), nullable=False)
    reference = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    wallet = relationship("Wallet", back_populates="transactions")


class WithdrawalRequest(Base):
    """Pending withdrawal requests that require admin approval for large amounts."""
    __tablename__ = "withdrawal_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    status = Column(
        Enum("pending", "approved", "rejected", name="withdrawal_status"),
        default="pending",
        nullable=False,
    )
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    review_note = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    wallet = relationship("Wallet")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
