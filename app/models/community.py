import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class CommunityTopic(Base):
    __tablename__ = "community_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    creator = relationship("User", foreign_keys=[created_by])


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("community_topics.id", ondelete="SET NULL"), nullable=True, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(
        Enum("discussion", "announcement", name="community_post_type"),
        nullable=False,
        default="discussion",
        index=True,
    )
    status = Column(
        Enum("published", "hidden", "removed", name="community_post_status"),
        nullable=False,
        default="published",
        index=True,
    )
    is_pinned = Column(Boolean, nullable=False, default=False)
    moderated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderation_note = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    topic = relationship("CommunityTopic")
    author = relationship("User", foreign_keys=[author_id])
    moderator = relationship("User", foreign_keys=[moderated_by])


class CommunityComment(Base):
    __tablename__ = "community_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    status = Column(
        Enum("published", "hidden", "removed", name="community_comment_status"),
        nullable=False,
        default="published",
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    post = relationship("CommunityPost")
    author = relationship("User", foreign_keys=[author_id])


class CommunityReaction(Base):
    __tablename__ = "community_reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_community_reaction_post_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    reaction = Column(
        Enum("like", "love", "celebrate", "support", "insightful", name="community_reaction_type"),
        nullable=False,
        default="like",
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    post = relationship("CommunityPost")
    user = relationship("User", foreign_keys=[user_id])


class CommunityPostFlag(Base):
    __tablename__ = "community_post_flags"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_community_flag_post_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(String(500), nullable=True)
    resolution = Column(
        Enum("pending", "dismissed", "actioned", name="community_flag_resolution"),
        nullable=False,
        default="pending",
        index=True,
    )
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    post = relationship("CommunityPost")
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class CommunitySubscription(Base):
    __tablename__ = "community_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_community_sub_user_topic"),
        UniqueConstraint("user_id", "post_id", name="uq_community_sub_user_post"),
        CheckConstraint(
            "(topic_id IS NOT NULL AND post_id IS NULL) OR (topic_id IS NULL AND post_id IS NOT NULL)",
            name="ck_community_subscription_one_target",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("community_topics.id", ondelete="CASCADE"), nullable=True, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    topic = relationship("CommunityTopic")
    post = relationship("CommunityPost")
