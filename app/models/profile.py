import enum
import uuid

from sqlalchemy import Boolean, Column, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class IdType(str, enum.Enum):
    NATIONAL = "NATIONAL"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    PASSPORT = "PASSPORT"


class EnglishLevel(str, enum.Enum):
    BASIC = "BASIC"
    ADVANCED = "ADVANCED"
    FLUENT = "FLUENT"


class ComputerExperience(str, enum.Enum):
    NO_EXPERIENCE = "NO_EXPERIENCE"
    YRS_0_2 = "YRS_0_2"
    YRS_2_5 = "YRS_2_5"
    YRS_5_PLUS = "YRS_5_PLUS"


class EducationLevel(str, enum.Enum):
    HIGHSCHOOL = "HIGHSCHOOL"
    CERTIFICATE = "CERTIFICATE"
    DIPLOMA = "DIPLOMA"
    DEGREE = "DEGREE"
    ADVANCED = "ADVANCED"


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Identification
    id_number = Column(String(100), nullable=True)
    id_type = Column(Enum(IdType, name="id_type_agent", native_enum=False), nullable=True)

    # Personal Details
    age = Column(Integer, nullable=True)
    town = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Professional & Skills
    education_level = Column(Enum(EducationLevel, name="education_level_enum", native_enum=False), default=EducationLevel.HIGHSCHOOL, nullable=True)
    english_level = Column(Enum(EnglishLevel, name="english_level_enum", native_enum=False), default=EnglishLevel.BASIC, nullable=True)
    computer_experience = Column(Enum(ComputerExperience, name="computer_exp_enum", native_enum=False), default=ComputerExperience.NO_EXPERIENCE, nullable=True)

    # Technical Infrastructure
    have_a_computer = Column(Boolean, default=False, nullable=False)
    access_to_internet = Column(Boolean, default=False, nullable=False)
    internet_speed = Column(String(100), nullable=True)

    # Personal Description
    description_of_self = Column(Text, nullable=True)

    # Availability
    availability = Column(String(50), nullable=True)  # e.g. "full-time", "part-time"
    hours_per_week_available = Column(String(50), nullable=True)

    # Metrics Tracking
    total_bookings = Column(Integer, default=0, nullable=False)
    total_refunds = Column(Integer, default=0, nullable=False)
    total_disputes = Column(Integer, default=0, nullable=False)
    avg_rating = Column(Float, default=0.0, nullable=False)
    hours_worked = Column(Float, default=0.0, nullable=False)
    quality_score = Column(Float, default=0.0, nullable=False)

    user = relationship("User", back_populates="agent_profile")


class PartnerProfile(Base):
    __tablename__ = "partner_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    contact_first_name = Column(String(255), nullable=True)
    contact_last_name = Column(String(255), nullable=True)
    id_number = Column(String(100), nullable=True)
    id_type = Column(Enum(IdType, name="id_type_partner", native_enum=False), nullable=True)
    business_name = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    description = Column(String(2000), nullable=True)
    services_provided = Column(ARRAY(String), default=list, nullable=True)
    availability = Column(String(50), nullable=True)
    hours_per_week_available = Column(String(50), nullable=True)

    # wallet relationship
    wallet = relationship("Wallet", back_populates="partner", uselist=False)
    user = relationship("User", back_populates="partner_profile")


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    user = relationship("User", back_populates="client_profile")
