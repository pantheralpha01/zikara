"""relax community flag resolver foreign key

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-10
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("community_post_flags_resolved_by_fkey", "community_post_flags", type_="foreignkey")
    op.create_foreign_key(
        "community_post_flags_resolved_by_fkey",
        "community_post_flags",
        "users",
        ["resolved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("community_post_flags_resolved_by_fkey", "community_post_flags", type_="foreignkey")
    op.create_foreign_key(
        "community_post_flags_resolved_by_fkey",
        "community_post_flags",
        "users",
        ["resolved_by"],
        ["id"],
    )
