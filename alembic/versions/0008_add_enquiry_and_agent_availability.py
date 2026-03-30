"""add enquiry table and agent availability fields

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- agent_profiles: round-robin assignment fields (IF NOT EXISTS) ---
    conn.execute(sa.text("ALTER TABLE agent_profiles ADD COLUMN IF NOT EXISTS availability_status VARCHAR(20) NOT NULL DEFAULT 'offline'"))
    conn.execute(sa.text("ALTER TABLE agent_profiles ADD COLUMN IF NOT EXISTS active_enquiry_count INTEGER NOT NULL DEFAULT 0"))
    conn.execute(sa.text("ALTER TABLE agent_profiles ADD COLUMN IF NOT EXISTS max_concurrent_enquiries INTEGER NOT NULL DEFAULT 5"))
    conn.execute(sa.text("ALTER TABLE agent_profiles ADD COLUMN IF NOT EXISTS last_assigned_at TIMESTAMPTZ"))

    # --- enquiries table (IF NOT EXISTS) ---
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id UUID PRIMARY KEY,
            chakra_enquiry_id VARCHAR(255) UNIQUE,
            agent_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'unassigned',
            title VARCHAR(500),
            notes TEXT,
            customer_name VARCHAR(255),
            customer_email VARCHAR(255),
            customer_phone VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            assigned_at TIMESTAMPTZ,
            closed_at TIMESTAMPTZ
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_enquiries_status ON enquiries (status)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_enquiries_agent_id ON enquiries (agent_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_enquiries_chakra_enquiry_id ON enquiries (chakra_enquiry_id)"))

    # --- bookings: link back to Chakra enquiry ---
    conn.execute(sa.text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS chakra_enquiry_id VARCHAR(255)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_bookings_chakra_enquiry_id ON bookings (chakra_enquiry_id)"))

    # --- quotes: link to Chakra enquiry ---
    conn.execute(sa.text("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS chakra_enquiry_id VARCHAR(255)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_quotes_chakra_enquiry_id ON quotes (chakra_enquiry_id)"))


def downgrade():
    op.drop_index("ix_quotes_chakra_enquiry_id", table_name="quotes")
    op.drop_column("quotes", "chakra_enquiry_id")

    op.drop_index("ix_bookings_chakra_enquiry_id", table_name="bookings")
    op.drop_column("bookings", "chakra_enquiry_id")

    op.drop_index("ix_enquiries_chakra_enquiry_id", table_name="enquiries")
    op.drop_index("ix_enquiries_agent_id", table_name="enquiries")
    op.drop_index("ix_enquiries_status", table_name="enquiries")
    op.drop_table("enquiries")

    op.drop_column("agent_profiles", "last_assigned_at")
    op.drop_column("agent_profiles", "max_concurrent_enquiries")
    op.drop_column("agent_profiles", "active_enquiry_count")
    op.drop_column("agent_profiles", "availability_status")
