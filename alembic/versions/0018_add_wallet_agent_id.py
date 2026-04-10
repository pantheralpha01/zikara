"""add missing wallets.agent_id column

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE wallets ADD COLUMN IF NOT EXISTS agent_id UUID"))
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'wallets_agent_id_fkey'
                ) THEN
                    ALTER TABLE wallets
                    ADD CONSTRAINT wallets_agent_id_fkey
                    FOREIGN KEY (agent_id) REFERENCES agent_profiles(id) ON DELETE CASCADE;
                END IF;
            END
            $$;
            """
        )
    )
    conn.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_wallets_agent_id ON wallets (agent_id)"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_wallets_agent_id"))
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'wallets_agent_id_fkey'
                ) THEN
                    ALTER TABLE wallets DROP CONSTRAINT wallets_agent_id_fkey;
                END IF;
            END
            $$;
            """
        )
    )
    conn.execute(sa.text("ALTER TABLE wallets DROP COLUMN IF EXISTS agent_id"))
