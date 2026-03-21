"""add full application fields to partner_profiles

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("partner_profiles", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("partner_profiles", sa.Column("town", sa.String(100), nullable=True))
    op.add_column("partner_profiles", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("partner_profiles", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("partner_profiles", sa.Column("business_address", sa.String(500), nullable=True))
    op.add_column("partner_profiles", sa.Column("business_phone", sa.String(100), nullable=True))
    op.add_column("partner_profiles", sa.Column("years_in_business", sa.Integer(), nullable=True))
    op.add_column("partner_profiles", sa.Column("service_areas", postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column("partner_profiles", sa.Column("languages_spoken", postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column("partner_profiles", sa.Column("english_level", sa.String(50), nullable=True))
    op.add_column("partner_profiles", sa.Column("computer_experience", sa.String(50), nullable=True))
    op.add_column("partner_profiles", sa.Column("have_a_computer", sa.Boolean(), nullable=True))
    op.add_column("partner_profiles", sa.Column("access_to_internet", sa.Boolean(), nullable=True))
    op.add_column("partner_profiles", sa.Column("internet_speed", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("partner_profiles", "internet_speed")
    op.drop_column("partner_profiles", "access_to_internet")
    op.drop_column("partner_profiles", "have_a_computer")
    op.drop_column("partner_profiles", "computer_experience")
    op.drop_column("partner_profiles", "english_level")
    op.drop_column("partner_profiles", "languages_spoken")
    op.drop_column("partner_profiles", "service_areas")
    op.drop_column("partner_profiles", "years_in_business")
    op.drop_column("partner_profiles", "business_phone")
    op.drop_column("partner_profiles", "business_address")
    op.drop_column("partner_profiles", "country")
    op.drop_column("partner_profiles", "city")
    op.drop_column("partner_profiles", "town")
    op.drop_column("partner_profiles", "age")
