"""add withdrawal_requests table

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(sa.text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'withdrawal_status') THEN "
            "CREATE TYPE withdrawal_status AS ENUM ('pending', 'approved', 'rejected'); "
            "END IF; END $$;"
        ))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS withdrawal_requests (
            id UUID PRIMARY KEY,
            wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
            amount NUMERIC(14, 2) NOT NULL,
            status withdrawal_status NOT NULL DEFAULT 'pending',
            requested_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reviewed_by UUID REFERENCES users(id),
            review_note VARCHAR(1000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            reviewed_at TIMESTAMPTZ
        )
    """))
    op.create_index("ix_withdrawal_requests_wallet_id", "withdrawal_requests", ["wallet_id"])
    op.create_index("ix_withdrawal_requests_requested_by", "withdrawal_requests", ["requested_by"])


def downgrade():
    op.drop_index("ix_withdrawal_requests_requested_by", table_name="withdrawal_requests")
    op.drop_index("ix_withdrawal_requests_wallet_id", table_name="withdrawal_requests")
    op.drop_table("withdrawal_requests")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS withdrawal_status")
