import uuid

from sqlalchemy import Boolean, Column, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    attributes_schema = Column(JSON, default=list, nullable=False)

    services = relationship("Service", back_populates="category")
    listings = relationship("Listing", back_populates="category")
