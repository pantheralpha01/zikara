"""add agent compensation fields

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_profiles", sa.Column("pay_per_hour", sa.Numeric(12, 2), nullable=True))
    op.add_column("agent_profiles", sa.Column("working_schedule", sa.String(length=500), nullable=True))

    op.execute("UPDATE agent_profiles SET pay_per_hour = 0 WHERE pay_per_hour IS NULL")
    op.alter_column("agent_profiles", "pay_per_hour", nullable=False)


def downgrade():
    op.drop_column("agent_profiles", "working_schedule")
    op.drop_column("agent_profiles", "pay_per_hour")
