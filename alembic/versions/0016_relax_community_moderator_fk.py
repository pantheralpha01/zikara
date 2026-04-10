"""relax community moderator foreign key

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-10
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("community_posts_moderated_by_fkey", "community_posts", type_="foreignkey")
    op.create_foreign_key(
        "community_posts_moderated_by_fkey",
        "community_posts",
        "users",
        ["moderated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("community_posts_moderated_by_fkey", "community_posts", type_="foreignkey")
    op.create_foreign_key(
        "community_posts_moderated_by_fkey",
        "community_posts",
        "users",
        ["moderated_by"],
        ["id"],
    )
