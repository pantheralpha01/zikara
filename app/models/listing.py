import uuid

from sqlalchemy import Column, Enum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_profiles.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    city = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    price_from = Column(Numeric(14, 2), nullable=True)
    pricing_type = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=True)
    attributes = Column(JSON, default=dict, nullable=False)
    status = Column(
        Enum("pending", "approved", "rejected", name="listing_status"),
        default="pending",
        nullable=False,
    )

    category = relationship("Category", back_populates="listings")
    service = relationship("Service", back_populates="listings")
    partner = relationship("PartnerProfile")
