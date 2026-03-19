"""
Nightly snapshot service.
Called by APScheduler at 00:05 UTC to persist aggregated stats for the previous day.
Can also be triggered manually via POST /admin/stats/snapshot.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingPartner
from app.models.payment import Wallet, WalletTransaction
from app.models.profile import PartnerProfile
from app.models.refund_dispute import Dispute, Refund
from app.models.review import Review
from app.models.stats import (
    AgentDailyStats,
    AgentStats,
    PartnerDailyStats,
    PartnerStats,
    PlatformStats,
)
from app.models.user import User
from app.models.worklog import AgentWorkLog


def _month_window(year: int, month: int):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _day_window(d: date):
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


# ── Platform ──────────────────────────────────────────────────────────────────


def _snapshot_platform(db: Session, target_date: date) -> None:
    day_start, day_end = _day_window(target_date)

    user_roles = {
        r: c
        for r, c in db.query(User.role, func.count(User.id))
        .filter(User.is_deleted == False)
        .group_by(User.role)
        .all()
    }
    new_users = {
        r: c
        for r, c in db.query(User.role, func.count(User.id))
        .filter(User.is_deleted == False, User.created_at >= day_start, User.created_at < day_end)
        .group_by(User.role)
        .all()
    }

    booking_counts = {
        s: c
        for s, c in db.query(Booking.status, func.count(Booking.id))
        .filter(Booking.created_at >= day_start, Booking.created_at < day_end)
        .group_by(Booking.status)
        .all()
    }

    now = datetime.now(timezone.utc)
    ongoing = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.status == "confirmed",
            Booking.service_start_at != None,
            Booking.service_start_at <= now,
        )
        .scalar()
        or 0
    )

    gross = float(
        db.query(func.sum(Booking.total_amount))
        .filter(Booking.created_at >= day_start, Booking.created_at < day_end, Booking.status != "cancelled")
        .scalar()
        or 0
    )

    refunds_total = float(
        db.query(func.sum(Refund.amount))
        .filter(Refund.status == "processed", Refund.updated_at >= day_start, Refund.updated_at < day_end)
        .scalar()
        or 0
    )

    disputes_opened = (
        db.query(func.count(Dispute.id))
        .filter(Dispute.created_at >= day_start, Dispute.created_at < day_end)
        .scalar()
        or 0
    )
    disputes_closed = (
        db.query(func.count(Dispute.id))
        .filter(
            Dispute.status.in_(["resolved", "closed"]),
            Dispute.updated_at >= day_start,
            Dispute.updated_at < day_end,
        )
        .scalar()
        or 0
    )

    rev_row = db.query(func.count(Review.id), func.avg(Review.rating)).first()

    wallet_row = db.query(
        func.sum(Wallet.escrow_balance),
        func.sum(Wallet.pending_balance),
    ).first()

    # Escrow funds held today = successful payments on this day
    escrow_held = float(
        db.query(func.sum(WalletTransaction.amount))
        .filter(
            WalletTransaction.type == "escrow_in",
            WalletTransaction.created_at >= day_start,
            WalletTransaction.created_at < day_end,
        )
        .scalar()
        or 0
    )
    # Payouts today
    payouts_today = float(
        db.query(func.sum(WalletTransaction.amount))
        .filter(
            WalletTransaction.type == "payout",
            WalletTransaction.created_at >= day_start,
            WalletTransaction.created_at < day_end,
        )
        .scalar()
        or 0
    )

    row = db.query(PlatformStats).filter(PlatformStats.date == target_date).first()
    data = dict(
        total_customers=user_roles.get("client", 0),
        total_agents=user_roles.get("agent", 0),
        total_partners=user_roles.get("partner", 0),
        new_customers=new_users.get("client", 0),
        new_agents=new_users.get("agent", 0),
        new_partners=new_users.get("partner", 0),
        bookings_created=sum(booking_counts.values()),
        bookings_confirmed=booking_counts.get("confirmed", 0),
        ongoing_bookings=ongoing,
        bookings_completed=booking_counts.get("completed", 0),
        bookings_cancelled=booking_counts.get("cancelled", 0),
        gross_booking_value=gross,
        refunds_issued=refunds_total,
        escrow_balance=float(wallet_row[0] or 0),
        escrow_funds_held=escrow_held,
        escrow_funds_released=payouts_today,
        escrow_pending_release=float(wallet_row[1] or 0),
        disputes_opened=disputes_opened,
        disputes_closed=disputes_closed,
        total_reviews=rev_row[0] or 0,
        average_rating=float(rev_row[1] or 0),
    )
    if row:
        for k, v in data.items():
            setattr(row, k, v)
    else:
        db.add(PlatformStats(date=target_date, **data))


# ── Agent ─────────────────────────────────────────────────────────────────────


def _compute_agent_stats(db: Session, agent_id, month: int, year: int) -> dict:
    start, end = _month_window(year, month)
    now = datetime.now(timezone.utc)

    total = (
        db.query(func.count(Booking.id))
        .filter(Booking.agent_id == agent_id, Booking.created_at >= start, Booking.created_at < end)
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.agent_id == agent_id,
            Booking.status == "completed",
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )
    cancelled = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.agent_id == agent_id,
            Booking.status == "cancelled",
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )
    ongoing = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.agent_id == agent_id,
            Booking.status == "confirmed",
            Booking.service_start_at != None,
            Booking.service_start_at <= now,
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )

    refunds = (
        db.query(func.count(Refund.id))
        .join(Booking, Refund.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Refund.created_at >= start, Refund.created_at < end)
        .scalar()
        or 0
    )
    disputes = (
        db.query(func.count(Dispute.id))
        .join(Booking, Dispute.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Dispute.created_at >= start, Dispute.created_at < end)
        .scalar()
        or 0
    )

    rev_row = (
        db.query(func.count(Review.id), func.avg(Review.rating))
        .join(Booking, Review.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Review.created_at >= start, Review.created_at < end)
        .first()
    )
    review_count = rev_row[0] or 0
    avg_rating = float(rev_row[1] or 0)

    five_star = (
        db.query(func.count(Review.id))
        .join(Booking, Review.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Review.rating == 5, Review.created_at >= start, Review.created_at < end)
        .scalar()
        or 0
    )

    hours = float(
        db.query(func.sum(AgentWorkLog.hours))
        .filter(AgentWorkLog.agent_id == agent_id, AgentWorkLog.clock_in >= start, AgentWorkLog.clock_in < end)
        .scalar()
        or 0
    )

    # Revenue from completed bookings in this period
    revenue = float(
        db.query(func.sum(Booking.total_amount))
        .filter(
            Booking.agent_id == agent_id,
            Booking.status == "completed",
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )

    # Active disputes (currently open/under_review — not filtered by month)
    active_disputes = (
        db.query(func.count(Dispute.id))
        .join(Booking, Dispute.booking_id == Booking.id)
        .filter(
            Booking.agent_id == agent_id,
            Dispute.status.in_(["open", "under_review"]),
        )
        .scalar()
        or 0
    )

    # Booking trends: last 6 months relative to the requested month/year
    trends = []
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        t_start, t_end = _month_window(y, m)
        count = (
            db.query(func.count(Booking.id))
            .filter(Booking.agent_id == agent_id, Booking.created_at >= t_start, Booking.created_at < t_end)
            .scalar()
            or 0
        )
        trends.append({"month": m, "year": y, "count": count})

    five_star_rate = (five_star / review_count * 100) if review_count > 0 else 0.0
    refund_rate = (refunds / total * 100) if total > 0 else 0.0
    dispute_rate = (disputes / total * 100) if total > 0 else 0.0
    booking_efficiency = (completed / total * 100) if total > 0 else 0.0
    quality_score = max(
        0.0,
        min(
            100.0,
            (avg_rating / 5 * 40)
            + (booking_efficiency / 100 * 40)
            + (max(0.0, 100.0 - refund_rate - dispute_rate) / 100 * 20),
        ),
    )

    return dict(
        total_bookings=total,
        ongoing_bookings=ongoing,
        completed_bookings=completed,
        cancelled_bookings=cancelled,
        total_refunds=refunds,
        total_disputes=disputes,
        active_disputes=active_disputes,
        review_count=review_count,
        average_rating=avg_rating,
        five_star_rate=five_star_rate,
        hours_worked=hours,
        revenue_generated=revenue,
        refund_rate=refund_rate,
        dispute_rate=dispute_rate,
        booking_efficiency=booking_efficiency,
        quality_score=quality_score,
        booking_trends=trends,
    )


def _compute_agent_daily(db: Session, agent_id, target_date: date) -> dict:
    day_start, day_end = _day_window(target_date)
    now = datetime.now(timezone.utc)

    handled = (
        db.query(func.count(Booking.id))
        .filter(Booking.agent_id == agent_id, Booking.created_at >= day_start, Booking.created_at < day_end)
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.agent_id == agent_id,
            Booking.status == "completed",
            Booking.updated_at >= day_start,
            Booking.updated_at < day_end,
        )
        .scalar()
        or 0
    )
    ongoing = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.agent_id == agent_id,
            Booking.status == "confirmed",
            Booking.service_start_at != None,
            Booking.service_start_at <= now,
        )
        .scalar()
        or 0
    )
    refunds = (
        db.query(func.count(Refund.id))
        .join(Booking, Refund.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Refund.created_at >= day_start, Refund.created_at < day_end)
        .scalar()
        or 0
    )
    disputes = (
        db.query(func.count(Dispute.id))
        .join(Booking, Dispute.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Dispute.created_at >= day_start, Dispute.created_at < day_end)
        .scalar()
        or 0
    )
    hours = float(
        db.query(func.sum(AgentWorkLog.hours))
        .filter(AgentWorkLog.agent_id == agent_id, AgentWorkLog.clock_in >= day_start, AgentWorkLog.clock_in < day_end)
        .scalar()
        or 0
    )
    rev_row = (
        db.query(func.count(Review.id), func.avg(Review.rating))
        .join(Booking, Review.booking_id == Booking.id)
        .filter(Booking.agent_id == agent_id, Review.created_at >= day_start, Review.created_at < day_end)
        .first()
    )

    return dict(
        bookings_handled=handled,
        ongoing_bookings=ongoing,
        completed_bookings=completed,
        refunds_handled=refunds,
        disputes_handled=disputes,
        hours_worked=hours,
        review_count=rev_row[0] or 0,
        average_rating=float(rev_row[1] or 0),
    )


def _snapshot_agents(db: Session, target_date: date) -> None:
    agents = db.query(User.id).filter(User.role == "agent", User.is_deleted == False).all()
    month, year = target_date.month, target_date.year

    for (agent_id,) in agents:
        # Monthly
        monthly_data = _compute_agent_stats(db, agent_id, month, year)
        row = (
            db.query(AgentStats)
            .filter(AgentStats.agent_id == agent_id, AgentStats.month == month, AgentStats.year == year)
            .first()
        )
        if row:
            for k, v in monthly_data.items():
                setattr(row, k, v)
        else:
            db.add(AgentStats(agent_id=agent_id, month=month, year=year, **monthly_data))

        # Daily
        daily_data = _compute_agent_daily(db, agent_id, target_date)
        drow = (
            db.query(AgentDailyStats)
            .filter(AgentDailyStats.agent_id == agent_id, AgentDailyStats.date == target_date)
            .first()
        )
        if drow:
            for k, v in daily_data.items():
                setattr(drow, k, v)
        else:
            db.add(AgentDailyStats(agent_id=agent_id, date=target_date, **daily_data))


# ── Partner ───────────────────────────────────────────────────────────────────


def _compute_partner_stats(db: Session, partner_id, month: int, year: int) -> dict:
    start, end = _month_window(year, month)
    now = datetime.now(timezone.utc)

    base = (
        db.query(func.count(BookingPartner.id))
        .join(Booking, BookingPartner.booking_id == Booking.id)
        .filter(BookingPartner.partner_id == partner_id, Booking.created_at >= start, Booking.created_at < end)
    )
    received = base.scalar() or 0

    completed = (
        db.query(func.count(BookingPartner.id))
        .join(Booking, BookingPartner.booking_id == Booking.id)
        .filter(
            BookingPartner.partner_id == partner_id,
            Booking.status == "completed",
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )
    cancelled = (
        db.query(func.count(BookingPartner.id))
        .join(Booking, BookingPartner.booking_id == Booking.id)
        .filter(
            BookingPartner.partner_id == partner_id,
            Booking.status == "cancelled",
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )
    ongoing = (
        db.query(func.count(BookingPartner.id))
        .join(Booking, BookingPartner.booking_id == Booking.id)
        .filter(
            BookingPartner.partner_id == partner_id,
            Booking.status == "confirmed",
            Booking.service_start_at != None,
            Booking.service_start_at <= now,
            Booking.created_at >= start,
            Booking.created_at < end,
        )
        .scalar()
        or 0
    )

    revenue = float(
        db.query(func.sum(BookingPartner.amount))
        .join(Booking, BookingPartner.booking_id == Booking.id)
        .filter(BookingPartner.partner_id == partner_id, Booking.created_at >= start, Booking.created_at < end)
        .scalar()
        or 0
    )

    # Payouts from wallet transactions
    wallet = (
        db.query(Wallet)
        .join(PartnerProfile, Wallet.partner_id == PartnerProfile.id)
        .filter(PartnerProfile.id == partner_id)
        .first()
    )
    pending = float(wallet.pending_balance if wallet else 0)
    payouts = float(
        db.query(func.sum(WalletTransaction.amount))
        .join(Wallet, WalletTransaction.wallet_id == Wallet.id)
        .join(PartnerProfile, Wallet.partner_id == PartnerProfile.id)
        .filter(
            PartnerProfile.id == partner_id,
            WalletTransaction.type == "payout",
            WalletTransaction.created_at >= start,
            WalletTransaction.created_at < end,
        )
        .scalar()
        or 0
    )

    rev_row = (
        db.query(func.count(Review.id), func.avg(Review.rating))
        .join(Booking, Review.booking_id == Booking.id)
        .join(BookingPartner, BookingPartner.booking_id == Booking.id)
        .filter(BookingPartner.partner_id == partner_id, Review.created_at >= start, Review.created_at < end)
        .first()
    )

    return dict(
        bookings_received=received,
        ongoing_bookings=ongoing,
        bookings_completed=completed,
        bookings_cancelled=cancelled,
        revenue_generated=revenue,
        payouts_received=payouts,
        pending_payouts=pending,
        review_count=rev_row[0] or 0,
        average_rating=float(rev_row[1] or 0),
    )


def _snapshot_partners(db: Session, target_date: date) -> None:
    partners = db.query(PartnerProfile.id).all()
    month, year = target_date.month, target_date.year

    for (partner_id,) in partners:
        data = _compute_partner_stats(db, partner_id, month, year)
        row = (
            db.query(PartnerStats)
            .filter(
                PartnerStats.partner_id == partner_id,
                PartnerStats.month == month,
                PartnerStats.year == year,
            )
            .first()
        )
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            db.add(PartnerStats(partner_id=partner_id, month=month, year=year, **data))

        # Daily partner stats — same as monthly but scoped to one day
        day_start, day_end = _day_window(target_date)
        daily_received = (
            db.query(func.count(BookingPartner.id))
            .join(Booking, BookingPartner.booking_id == Booking.id)
            .filter(
                BookingPartner.partner_id == partner_id,
                Booking.created_at >= day_start,
                Booking.created_at < day_end,
            )
            .scalar()
            or 0
        )
        daily_completed = (
            db.query(func.count(BookingPartner.id))
            .join(Booking, BookingPartner.booking_id == Booking.id)
            .filter(
                BookingPartner.partner_id == partner_id,
                Booking.status == "completed",
                Booking.updated_at >= day_start,
                Booking.updated_at < day_end,
            )
            .scalar()
            or 0
        )
        daily_revenue = float(
            db.query(func.sum(BookingPartner.amount))
            .join(Booking, BookingPartner.booking_id == Booking.id)
            .filter(
                BookingPartner.partner_id == partner_id,
                Booking.created_at >= day_start,
                Booking.created_at < day_end,
            )
            .scalar()
            or 0
        )
        daily_rev_row = (
            db.query(func.count(Review.id), func.avg(Review.rating))
            .join(Booking, Review.booking_id == Booking.id)
            .join(BookingPartner, BookingPartner.booking_id == Booking.id)
            .filter(
                BookingPartner.partner_id == partner_id,
                Review.created_at >= day_start,
                Review.created_at < day_end,
            )
            .first()
        )

        drow = (
            db.query(PartnerDailyStats)
            .filter(PartnerDailyStats.partner_id == partner_id, PartnerDailyStats.date == target_date)
            .first()
        )
        daily_data = dict(
            bookings_received=daily_received,
            bookings_completed=daily_completed,
            revenue_generated=daily_revenue,
            review_count=daily_rev_row[0] or 0,
            average_rating=float(daily_rev_row[1] or 0),
        )
        if drow:
            for k, v in daily_data.items():
                setattr(drow, k, v)
        else:
            db.add(PartnerDailyStats(partner_id=partner_id, date=target_date, **daily_data))


# ── Public entry point ────────────────────────────────────────────────────────


def take_daily_snapshot(db: Session, target_date: date | None = None) -> None:
    """Compute and persist stats for target_date (defaults to yesterday)."""
    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    try:
        _snapshot_platform(db, target_date)
        _snapshot_agents(db, target_date)
        _snapshot_partners(db, target_date)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
