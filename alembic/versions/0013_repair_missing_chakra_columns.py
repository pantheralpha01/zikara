"""repair missing chakra linkage columns

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS chakra_enquiry_id VARCHAR(255)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_bookings_chakra_enquiry_id ON bookings (chakra_enquiry_id)"))
    conn.execute(sa.text("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS chakra_enquiry_id VARCHAR(255)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_quotes_chakra_enquiry_id ON quotes (chakra_enquiry_id)"))


def downgrade():
    op.drop_index("ix_quotes_chakra_enquiry_id", table_name="quotes")
    op.drop_column("quotes", "chakra_enquiry_id")
    op.drop_index("ix_bookings_chakra_enquiry_id", table_name="bookings")
    op.drop_column("bookings", "chakra_enquiry_id")
