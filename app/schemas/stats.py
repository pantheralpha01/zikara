from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class BookingTrendPoint(BaseModel):
    month: int
    year: int
    count: int


class AgentWeeklyHoursOut(BaseModel):
    agent_id: UUID
    full_name: Optional[str] = None
    hours_this_week: float = 0


class PlatformStatsOut(BaseModel):
    # Users
    total_customers: int = 0
    total_agents: int = 0
    total_partners: int = 0
    new_customers_today: int = 0
    new_agents_today: int = 0
    new_partners_today: int = 0

    # Bookings
    bookings_total: int = 0
    bookings_confirmed: int = 0
    ongoing_bookings: int = 0
    bookings_completed: int = 0
    bookings_cancelled: int = 0

    # Financial
    gross_booking_value: float = 0
    total_amount_paid: float = 0
    refunds_issued: float = 0
    total_payouts: float = 0        # sum of all 'payout' wallet transactions
    platform_profit: float = 0      # gross - payouts - refunds
    taxes_collected: float = 0      # placeholder: populate when tax model is added

    # Escrow
    escrow_balance: float = 0
    available_balance: float = 0
    pending_balance: float = 0

    # Operations
    disputes_open: int = 0
    disputes_closed: int = 0

    # Reviews
    total_reviews: int = 0
    average_rating: float = 0


class AgentStatsOut(BaseModel):
    agent_id: UUID
    month: int
    year: int
    total_bookings: int = 0
    ongoing_bookings: int = 0
    completed_bookings: int = 0
    cancelled_bookings: int = 0
    total_refunds: int = 0
    total_disputes: int = 0
    active_disputes: int = 0        # currently open/under_review (not filtered by month)
    review_count: int = 0
    average_rating: float = 0
    five_star_rate: float = 0
    hours_worked: float = 0
    revenue_generated: float = 0    # sum of completed booking amounts in period
    refund_rate: float = 0
    dispute_rate: float = 0
    booking_efficiency: float = 0
    quality_score: float = 0
    booking_trends: List[BookingTrendPoint] = []  # last 6 months relative to queried month


class PartnerStatsOut(BaseModel):
    partner_id: UUID
    month: int
    year: int
    bookings_received: int = 0
    ongoing_bookings: int = 0
    bookings_completed: int = 0
    bookings_cancelled: int = 0
    revenue_generated: float = 0
    payouts_received: float = 0
    pending_payouts: float = 0
    review_count: int = 0
    average_rating: float = 0


class WorkLogOut(BaseModel):
    id: UUID
    agent_id: UUID
    clock_in: datetime
    clock_out: Optional[datetime] = None
    hours: float = 0

    model_config = {"from_attributes": True}
