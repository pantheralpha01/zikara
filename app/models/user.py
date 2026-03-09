import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    gender = Column(Enum(Gender, name="gender_type", native_enum=False), nullable=True)
    profile_pic_url = Column(String(500), nullable=True)
    role = Column(Enum("admin", "agent", "partner", "client", name="user_role"), nullable=False)
    status = Column(
        Enum("active", "pending", "suspended", "rejected", name="user_status"),
        default="active",
        nullable=False,
    )
    refresh_token = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # role-specific extensions
    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False)
    partner_profile = relationship("PartnerProfile", back_populates="user", uselist=False)
    client_profile = relationship("ClientProfile", back_populates="user", uselist=False)
