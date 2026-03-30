from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.booking import Booking, BookingPartner
from app.models.payment import Wallet, WalletTransaction
from app.models.profile import PartnerProfile
from app.models.refund_dispute import Dispute, Refund
from app.models.review import Review
from app.models.user import User
from app.models.worklog import AgentWorkLog
from app.schemas.stats import (
    AgentStatsOut,
    AgentWeeklyHoursOut,
    PartnerStatsOut,
    PlatformStatsOut,
    WorkLogOut,
)
from app.services.snapshot import _compute_agent_stats, _compute_partner_stats, take_daily_snapshot

router = APIRouter(prefix="/admin", tags=["Admin Stats"])


# ── Platform overview ─────────────────────────────────────────────────────────


@router.get(
    "/stats/platform",
    response_model=PlatformStatsOut,
    summary="Live platform overview",
    description=(
        "Returns real-time aggregated platform metrics. "
        "Accessible only to admin and manager roles."
    ),
)
def platform_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    today = date.today()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    user_roles = {
        r: c
        for r, c in db.query(User.role, func.count(User.id))
        .filter(User.is_deleted == False)
        .group_by(User.role)
        .all()
    }
    new_today = {
        r: c
        for r, c in db.query(User.role, func.count(User.id))
        .filter(User.is_deleted == False, User.created_at >= today_start)
        .group_by(User.role)
        .all()
    }

    booking_counts = {
        s: c
        for s, c in db.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()
    }
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
        db.query(func.sum(Booking.total_amount)).filter(Booking.status != "cancelled").scalar() or 0
    )
    total_paid = float(db.query(func.sum(Booking.amount_paid)).scalar() or 0)

    refunds_total = float(
        db.query(func.sum(Refund.amount)).filter(Refund.status == "completed").scalar() or 0
    )

    total_payouts = float(
        db.query(func.sum(WalletTransaction.amount))
        .filter(WalletTransaction.type == "payout")
        .scalar() or 0
    )
    platform_profit = max(0.0, gross - total_payouts - refunds_total)

    disputes_open = (
        db.query(func.count(Dispute.id))
        .filter(Dispute.status.in_(["pending", "under_review"]))
        .scalar()
        or 0
    )
    disputes_closed = (
        db.query(func.count(Dispute.id))
        .filter(Dispute.status.in_(["resolved", "closed"]))
        .scalar()
        or 0
    )

    rev_row = db.query(func.count(Review.id), func.avg(Review.rating)).first()

    wallet_row = db.query(
        func.sum(Wallet.escrow_balance),
        func.sum(Wallet.available_balance),
        func.sum(Wallet.pending_balance),
    ).first()

    return PlatformStatsOut(
        total_customers=user_roles.get("client", 0),
        total_agents=user_roles.get("agent", 0),
        total_partners=user_roles.get("partner", 0),
        new_customers_today=new_today.get("client", 0),
        new_agents_today=new_today.get("agent", 0),
        new_partners_today=new_today.get("partner", 0),
        bookings_total=sum(booking_counts.values()),
        bookings_confirmed=booking_counts.get("confirmed", 0),
        ongoing_bookings=ongoing,
        bookings_completed=booking_counts.get("completed", 0),
        bookings_cancelled=booking_counts.get("cancelled", 0),
        gross_booking_value=gross,
        total_amount_paid=total_paid,
        refunds_issued=refunds_total,
        total_payouts=total_payouts,
        platform_profit=platform_profit,
        taxes_collected=0.0,
        escrow_balance=float(wallet_row[0] or 0),
        available_balance=float(wallet_row[1] or 0),
        pending_balance=float(wallet_row[2] or 0),
        disputes_open=disputes_open,
        disputes_closed=disputes_closed,
        total_reviews=rev_row[0] or 0,
        average_rating=float(rev_row[1] or 0),
    )


# ── Agent stats ───────────────────────────────────────────────────────────────


@router.get(
    "/stats/agents/{agent_id}",
    response_model=AgentStatsOut,
    summary="Agent monthly stats",
    description=(
        "Returns monthly performance metrics for an agent. "
        "Agents may only view their own stats; admin and manager can view any agent."
    ),
)
def agent_stats(
    agent_id: UUID,
    month: int = Query(default=None, ge=1, le=12, description="Month (1-12). Defaults to current month."),
    year: int = Query(default=None, ge=2020, description="Year. Defaults to current year."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"admin", "manager"} and str(current_user.id) != str(agent_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year

    data = _compute_agent_stats(db, agent_id, month, year)
    return AgentStatsOut(agent_id=agent_id, month=month, year=year, **data)


# ── Partner stats ─────────────────────────────────────────────────────────────


@router.get(
    "/stats/partners/{partner_id}",
    response_model=PartnerStatsOut,
    summary="Partner monthly stats",
    description=(
        "Returns monthly performance metrics for a partner profile. "
        "Partners may only view their own stats; admin and manager can view any partner."
    ),
)
def partner_stats(
    partner_id: UUID,
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"admin", "manager"}:
        if current_user.role == "partner":
            profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
            if not profile or profile.id != partner_id:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year

    data = _compute_partner_stats(db, partner_id, month, year)
    return PartnerStatsOut(partner_id=partner_id, month=month, year=year, **data)


# ── Work logs ─────────────────────────────────────────────────────────────────


@router.get(
    "/worklogs",
    response_model=list[WorkLogOut],
    summary="List agent work logs",
    description=(
        "Returns work log entries (clock-in / clock-out). "
        "Admins and managers see all agents; agents see only their own entries."
    ),
)
def list_worklogs(
    agent_id: Optional[UUID] = Query(None, description="Filter by agent user ID"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AgentWorkLog)

    if current_user.role not in {"admin", "manager"}:
        if current_user.role != "agent":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        q = q.filter(AgentWorkLog.agent_id == current_user.id)
    elif agent_id:
        q = q.filter(AgentWorkLog.agent_id == agent_id)

    if date_from:
        q = q.filter(AgentWorkLog.clock_in >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc))
    if date_to:
        q = q.filter(AgentWorkLog.clock_in < datetime(date_to.year, date_to.month, date_to.day + 1, tzinfo=timezone.utc))

    return [WorkLogOut.model_validate(w) for w in q.order_by(AgentWorkLog.clock_in.desc()).all()]


@router.post(
    "/worklogs/{log_id}/clockout",
    response_model=WorkLogOut,
    summary="Manual clock-out",
    description="Force-close an open work log entry. Useful when a session expires without an explicit logout.",
)
def manual_clockout(
    log_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = db.query(AgentWorkLog).filter(AgentWorkLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")
    if current_user.role not in {"admin", "manager"} and str(log.agent_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if log.clock_out is not None:
        raise HTTPException(status_code=400, detail="Work log already closed")

    now = datetime.now(timezone.utc)
    log.clock_out = now
    log.hours = (now - log.clock_in).total_seconds() / 3600
    db.commit()
    db.refresh(log)
    return WorkLogOut.model_validate(log)


# ── Snapshot trigger ──────────────────────────────────────────────────────────


@router.post(
    "/stats/snapshot",
    status_code=200,
    summary="Manually trigger daily snapshot",
    description=(
        "Computes and persists stat snapshots for the given date (defaults to yesterday). "
        "Normally run automatically by the nightly scheduler at 00:05 UTC."
    ),
)
def trigger_snapshot(
    target_date: Optional[date] = Query(None, description="Date to snapshot (YYYY-MM-DD). Defaults to yesterday."),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    from app.db.session import SessionLocal

    take_daily_snapshot(SessionLocal(), target_date)
    return {"message": f"Snapshot completed for {target_date or 'yesterday'}"}


# ── Clock-in / Clock-out ──────────────────────────────────────────────────────


@router.post(
    "/worklogs/clockin",
    response_model=WorkLogOut,
    status_code=201,
    summary="Agent clock-in",
    description="Starts a new work log entry for the calling agent. Fails if there is already an open (un-closed) entry.",
)
def agent_clockin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    open_log = (
        db.query(AgentWorkLog)
        .filter(AgentWorkLog.agent_id == current_user.id, AgentWorkLog.clock_out == None)
        .first()
    )
    if open_log:
        raise HTTPException(status_code=400, detail="You already have an open shift. Clock out first.")

    log = AgentWorkLog(
        agent_id=current_user.id,
        clock_in=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return WorkLogOut.model_validate(log)


@router.post(
    "/worklogs/clockout",
    response_model=WorkLogOut,
    status_code=200,
    summary="Agent clock-out",
    description="Closes the calling agent's currently open work log entry.",
)
def agent_clockout(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    log = (
        db.query(AgentWorkLog)
        .filter(AgentWorkLog.agent_id == current_user.id, AgentWorkLog.clock_out == None)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="No open shift found. Clock in first.")

    now = datetime.now(timezone.utc)
    log.clock_out = now
    log.hours = (now - log.clock_in).total_seconds() / 3600
    db.commit()
    db.refresh(log)
    return WorkLogOut.model_validate(log)


# ── Weekly agent hours listing ────────────────────────────────────────────────


@router.get(
    "/stats/agents/hours-weekly",
    response_model=List[AgentWeeklyHoursOut],
    summary="Agent hours worked this week",
    description=(
        "Returns a list of all agents with total hours worked in the current ISO week "
        "(Monday 00:00 UTC → now). Accessible to admin and manager."
    ),
)
def agent_hours_weekly(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    rows = (
        db.query(AgentWorkLog.agent_id, func.sum(AgentWorkLog.hours).label("total_hours"))
        .filter(AgentWorkLog.clock_in >= week_start)
        .group_by(AgentWorkLog.agent_id)
        .all()
    )

    result = []
    for agent_id, hours in rows:
        user = db.query(User).filter(User.id == agent_id).first()
        result.append(
            AgentWeeklyHoursOut(
                agent_id=agent_id,
                full_name=user.full_name if user else None,
                hours_this_week=float(hours or 0),
            )
        )
    return result
