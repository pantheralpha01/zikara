"""add user email verification fields

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True))
    op.add_column("users", sa.Column("email_verification_sent_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE users SET email_verified = false WHERE email_verified IS NULL")
    op.alter_column("users", "email_verified", nullable=False)


def downgrade():
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verified")
