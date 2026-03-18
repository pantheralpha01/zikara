"""add booking_partners, agent_work_logs, wallet_transactions, and all stats tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ── booking_partners ──────────────────────────────────────────────────────
    op.create_table(
        "booking_partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_booking_partners_booking_id", "booking_partners", ["booking_id"])
    op.create_index("ix_booking_partners_partner_id", "booking_partners", ["partner_id"])

    # ── agent_work_logs ───────────────────────────────────────────────────────
    op.create_table(
        "agent_work_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clock_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_work_logs_agent_id", "agent_work_logs", ["agent_id"])

    # ── wallet_transactions ───────────────────────────────────────────────────
    # Create the enum type first, then the table — both via raw SQL so that
    # SQLAlchemy's Enum _on_table_create event never fires during this migration.
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(
            "CREATE TYPE wallet_tx_type AS ENUM "
            "('escrow_in', 'escrow_release', 'payout', 'refund_debit')"
        ))
    op.execute(sa.text("""
        CREATE TABLE wallet_transactions (
            id          UUID PRIMARY KEY,
            wallet_id   UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
            type        wallet_tx_type NOT NULL,
            amount      NUMERIC(14, 2) NOT NULL,
            reference   VARCHAR(500),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])

    # ── platform_stats ────────────────────────────────────────────────────────
    op.create_table(
        "platform_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date, nullable=False, unique=True),
        sa.Column("total_customers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_agents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_partners", sa.Integer, nullable=False, server_default="0"),
        sa.Column("new_customers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("new_agents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("new_partners", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_confirmed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ongoing_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_cancelled", sa.Integer, nullable=False, server_default="0"),
        sa.Column("gross_booking_value", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("platform_revenue", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("partner_payouts", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("refunds_issued", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("escrow_balance", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("escrow_funds_held", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("escrow_funds_released", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("escrow_pending_release", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("disputes_opened", sa.Integer, nullable=False, server_default="0"),
        sa.Column("disputes_closed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_reviews", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_platform_stats_date", "platform_stats", ["date"])

    # ── agent_stats ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("total_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ongoing_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cancelled_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_refunds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_disputes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float, nullable=False, server_default="0"),
        sa.Column("five_star_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("hours_worked", sa.Float, nullable=False, server_default="0"),
        sa.Column("refund_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("dispute_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("booking_efficiency", sa.Float, nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", "month", "year", name="uq_agent_stats_month"),
    )
    op.create_index("ix_agent_stats_agent_id", "agent_stats", ["agent_id"])

    # ── agent_daily_stats ─────────────────────────────────────────────────────
    op.create_table(
        "agent_daily_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("bookings_handled", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ongoing_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("refunds_handled", sa.Integer, nullable=False, server_default="0"),
        sa.Column("disputes_handled", sa.Integer, nullable=False, server_default="0"),
        sa.Column("hours_worked", sa.Float, nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", "date", name="uq_agent_daily_stats"),
    )
    op.create_index("ix_agent_daily_stats_agent_id", "agent_daily_stats", ["agent_id"])

    # ── partner_stats ─────────────────────────────────────────────────────────
    op.create_table(
        "partner_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("bookings_received", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ongoing_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_cancelled", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revenue_generated", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payouts_received", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("pending_payouts", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("partner_id", "month", "year", name="uq_partner_stats_month"),
    )
    op.create_index("ix_partner_stats_partner_id", "partner_stats", ["partner_id"])

    # ── partner_daily_stats ───────────────────────────────────────────────────
    op.create_table(
        "partner_daily_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("bookings_received", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ongoing_bookings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bookings_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revenue_generated", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("partner_id", "date", name="uq_partner_daily_stats"),
    )
    op.create_index("ix_partner_daily_stats_partner_id", "partner_daily_stats", ["partner_id"])


def downgrade():
    op.drop_table("partner_daily_stats")
    op.drop_table("partner_stats")
    op.drop_table("agent_daily_stats")
    op.drop_table("agent_stats")
    op.drop_table("platform_stats")
    op.drop_table("wallet_transactions")
    op.drop_index("ix_agent_work_logs_agent_id", "agent_work_logs")
    op.drop_table("agent_work_logs")
    op.drop_index("ix_booking_partners_partner_id", "booking_partners")
    op.drop_index("ix_booking_partners_booking_id", "booking_partners")
    op.drop_table("booking_partners")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS wallet_tx_type")
