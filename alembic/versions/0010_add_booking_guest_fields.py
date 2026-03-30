"""add booking guest fields and special notes

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(sa.text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_residency') THEN "
            "CREATE TYPE booking_residency AS ENUM ('CITIZEN', 'RESIDENT', 'NON-RESIDENT'); "
            "END IF; END $$;"
        ))

    op.add_column("bookings", sa.Column("number_of_adults", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("number_of_children", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("number_of_infants", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("residency", sa.Enum("CITIZEN", "RESIDENT", "NON-RESIDENT", name="booking_residency"), nullable=True))
    op.add_column("bookings", sa.Column("pets", sa.Boolean(), nullable=True))
    op.add_column("bookings", sa.Column("pickup_location", sa.String(length=255), nullable=True))
    op.add_column("bookings", sa.Column("destination_location", sa.String(length=255), nullable=True))
    op.add_column("bookings", sa.Column("special_notes", sa.String(length=1000), nullable=True))

    op.execute("UPDATE bookings SET number_of_adults = 0 WHERE number_of_adults IS NULL")
    op.execute("UPDATE bookings SET number_of_children = 0 WHERE number_of_children IS NULL")
    op.execute("UPDATE bookings SET number_of_infants = 0 WHERE number_of_infants IS NULL")
    op.execute("UPDATE bookings SET pets = false WHERE pets IS NULL")

    op.alter_column("bookings", "number_of_adults", nullable=False)
    op.alter_column("bookings", "number_of_children", nullable=False)
    op.alter_column("bookings", "number_of_infants", nullable=False)
    op.alter_column("bookings", "pets", nullable=False)


def downgrade():
    op.drop_column("bookings", "special_notes")
    op.drop_column("bookings", "destination_location")
    op.drop_column("bookings", "pickup_location")
    op.drop_column("bookings", "pets")
    op.drop_column("bookings", "residency")
    op.drop_column("bookings", "number_of_infants")
    op.drop_column("bookings", "number_of_children")
    op.drop_column("bookings", "number_of_adults")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS booking_residency")
