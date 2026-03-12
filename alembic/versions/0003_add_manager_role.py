"""add manager role to user_role enum

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'manager'")


def downgrade():
    # PostgreSQL enum value removal is non-trivial and unsafe in downgrade.
    pass
