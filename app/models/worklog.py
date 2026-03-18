import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AgentWorkLog(Base):
    __tablename__ = "agent_work_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    hours = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent = relationship("User", foreign_keys=[agent_id])
