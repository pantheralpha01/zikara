"""add community module tables

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "community_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_community_topics_name"), "community_topics", ["name"], unique=True)

    post_type = sa.Enum("discussion", "announcement", name="community_post_type")
    post_type.create(op.get_bind(), checkfirst=True)
    post_status = sa.Enum("published", "hidden", "removed", name="community_post_status")
    post_status.create(op.get_bind(), checkfirst=True)
    comment_status = sa.Enum("published", "hidden", "removed", name="community_comment_status")
    comment_status.create(op.get_bind(), checkfirst=True)
    reaction_type = sa.Enum("like", "love", "celebrate", "support", "insightful", name="community_reaction_type")
    reaction_type.create(op.get_bind(), checkfirst=True)
    flag_resolution = sa.Enum("pending", "dismissed", "actioned", name="community_flag_resolution")
    flag_resolution.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "community_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("post_type", post_type, nullable=False),
        sa.Column("status", post_status, nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("moderated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("moderation_note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["moderated_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["community_topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_community_posts_author_id"), "community_posts", ["author_id"], unique=False)
    op.create_index(op.f("ix_community_posts_post_type"), "community_posts", ["post_type"], unique=False)
    op.create_index(op.f("ix_community_posts_status"), "community_posts", ["status"], unique=False)
    op.create_index(op.f("ix_community_posts_topic_id"), "community_posts", ["topic_id"], unique=False)

    op.create_table(
        "community_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", comment_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_community_comments_author_id"), "community_comments", ["author_id"], unique=False)
    op.create_index(op.f("ix_community_comments_post_id"), "community_comments", ["post_id"], unique=False)
    op.create_index(op.f("ix_community_comments_status"), "community_comments", ["status"], unique=False)

    op.create_table(
        "community_reactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reaction", reaction_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_reaction_post_user"),
    )
    op.create_index(op.f("ix_community_reactions_post_id"), "community_reactions", ["post_id"], unique=False)
    op.create_index(op.f("ix_community_reactions_user_id"), "community_reactions", ["user_id"], unique=False)

    op.create_table(
        "community_post_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("resolution", flag_resolution, nullable=False),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_flag_post_user"),
    )
    op.create_index(op.f("ix_community_post_flags_post_id"), "community_post_flags", ["post_id"], unique=False)
    op.create_index(op.f("ix_community_post_flags_resolution"), "community_post_flags", ["resolution"], unique=False)
    op.create_index(op.f("ix_community_post_flags_user_id"), "community_post_flags", ["user_id"], unique=False)

    op.create_table(
        "community_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(topic_id IS NOT NULL AND post_id IS NULL) OR (topic_id IS NULL AND post_id IS NOT NULL)",
            name="ck_community_subscription_one_target",
        ),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["community_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_community_sub_user_post"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_community_sub_user_topic"),
    )
    op.create_index(op.f("ix_community_subscriptions_post_id"), "community_subscriptions", ["post_id"], unique=False)
    op.create_index(op.f("ix_community_subscriptions_topic_id"), "community_subscriptions", ["topic_id"], unique=False)
    op.create_index(op.f("ix_community_subscriptions_user_id"), "community_subscriptions", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_community_subscriptions_user_id"), table_name="community_subscriptions")
    op.drop_index(op.f("ix_community_subscriptions_topic_id"), table_name="community_subscriptions")
    op.drop_index(op.f("ix_community_subscriptions_post_id"), table_name="community_subscriptions")
    op.drop_table("community_subscriptions")

    op.drop_index(op.f("ix_community_post_flags_user_id"), table_name="community_post_flags")
    op.drop_index(op.f("ix_community_post_flags_resolution"), table_name="community_post_flags")
    op.drop_index(op.f("ix_community_post_flags_post_id"), table_name="community_post_flags")
    op.drop_table("community_post_flags")

    op.drop_index(op.f("ix_community_reactions_user_id"), table_name="community_reactions")
    op.drop_index(op.f("ix_community_reactions_post_id"), table_name="community_reactions")
    op.drop_table("community_reactions")

    op.drop_index(op.f("ix_community_comments_status"), table_name="community_comments")
    op.drop_index(op.f("ix_community_comments_post_id"), table_name="community_comments")
    op.drop_index(op.f("ix_community_comments_author_id"), table_name="community_comments")
    op.drop_table("community_comments")

    op.drop_index(op.f("ix_community_posts_topic_id"), table_name="community_posts")
    op.drop_index(op.f("ix_community_posts_status"), table_name="community_posts")
    op.drop_index(op.f("ix_community_posts_post_type"), table_name="community_posts")
    op.drop_index(op.f("ix_community_posts_author_id"), table_name="community_posts")
    op.drop_table("community_posts")

    op.drop_index(op.f("ix_community_topics_name"), table_name="community_topics")
    op.drop_table("community_topics")

    sa.Enum(name="community_flag_resolution").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="community_reaction_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="community_comment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="community_post_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="community_post_type").drop(op.get_bind(), checkfirst=True)
