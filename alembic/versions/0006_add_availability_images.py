"""add availability, hours_per_week_available to agent/partner profiles; add images to listings

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    # agent_profiles
    op.add_column("agent_profiles", sa.Column("availability", sa.String(50), nullable=True))
    op.add_column("agent_profiles", sa.Column("hours_per_week_available", sa.String(50), nullable=True))

    # partner_profiles
    op.add_column("partner_profiles", sa.Column("availability", sa.String(50), nullable=True))
    op.add_column("partner_profiles", sa.Column("hours_per_week_available", sa.String(50), nullable=True))

    # listings — JSON array of image URLs
    op.add_column("listings", sa.Column("images", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("listings", "images")
    op.drop_column("partner_profiles", "hours_per_week_available")
    op.drop_column("partner_profiles", "availability")
    op.drop_column("agent_profiles", "hours_per_week_available")
    op.drop_column("agent_profiles", "availability")
