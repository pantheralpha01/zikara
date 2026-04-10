"""relax community user foreign keys for cleanup safety

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("community_topics", "created_by", existing_type=sa.UUID(), nullable=True)
    op.drop_constraint("community_topics_created_by_fkey", "community_topics", type_="foreignkey")
    op.create_foreign_key(
        "community_topics_created_by_fkey",
        "community_topics",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("community_posts", "author_id", existing_type=sa.UUID(), nullable=True)
    op.drop_constraint("community_posts_author_id_fkey", "community_posts", type_="foreignkey")
    op.create_foreign_key(
        "community_posts_author_id_fkey",
        "community_posts",
        "users",
        ["author_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("community_posts_author_id_fkey", "community_posts", type_="foreignkey")
    op.create_foreign_key(
        "community_posts_author_id_fkey",
        "community_posts",
        "users",
        ["author_id"],
        ["id"],
    )
    op.alter_column("community_posts", "author_id", existing_type=sa.UUID(), nullable=False)

    op.drop_constraint("community_topics_created_by_fkey", "community_topics", type_="foreignkey")
    op.create_foreign_key(
        "community_topics_created_by_fkey",
        "community_topics",
        "users",
        ["created_by"],
        ["id"],
    )
    op.alter_column("community_topics", "created_by", existing_type=sa.UUID(), nullable=False)
