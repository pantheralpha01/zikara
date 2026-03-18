"""add amount_paid and payment_status to bookings

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            "DO $$ BEGIN "
            "CREATE TYPE booking_payment_status AS ENUM ('unpaid', 'partially_paid', 'fully_paid'); "
            "EXCEPTION WHEN duplicate_object THEN null; "
            "END $$;"
        )

    op.add_column(
        "bookings",
        sa.Column("amount_paid", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "bookings",
        sa.Column(
            "payment_status",
            sa.Enum("unpaid", "partially_paid", "fully_paid", name="booking_payment_status"),
            nullable=False,
            server_default="unpaid",
        ),
    )


def downgrade():
    op.drop_column("bookings", "payment_status")
    op.drop_column("bookings", "amount_paid")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS booking_payment_status")
