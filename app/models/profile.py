import uuid

from sqlalchemy import Column, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    id_number = Column(String(100), nullable=True)
    id_type = Column(String(100), nullable=True)

    user = relationship("User", back_populates="agent_profile")


class PartnerProfile(Base):
    __tablename__ = "partner_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    contact_first_name = Column(String(255), nullable=True)
    contact_last_name = Column(String(255), nullable=True)
    id_number = Column(String(100), nullable=True)
    id_type = Column(String(100), nullable=True)
    business_name = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    description = Column(String(2000), nullable=True)

    # wallet relationship
    wallet = relationship("Wallet", back_populates="partner", uselist=False)
    user = relationship("User", back_populates="partner_profile")


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    user = relationship("User", back_populates="client_profile")
