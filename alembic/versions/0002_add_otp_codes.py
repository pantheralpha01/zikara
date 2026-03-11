"""add otp_codes table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "otp_codes" not in inspector.get_table_names():
        op.create_table(
            "otp_codes",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("phone", sa.String(20), nullable=False),
            sa.Column("code", sa.String(6), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_otp_codes_phone", "otp_codes", ["phone"])


def downgrade():
    op.drop_index("ix_otp_codes_phone", table_name="otp_codes")
    op.drop_table("otp_codes")
