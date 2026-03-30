from datetime import datetime, timezone

from sqlalchemy import asc, nullsfirst
from sqlalchemy.orm import Session

from app.models.enquiry import Enquiry
from app.models.profile import AgentProfile
from app.models.user import User
from app.services.chakra import notify_agent_assigned


def _pick_next_agent(db: Session) -> AgentProfile | None:
    """
    Round-robin: from all 'available' agents, pick the one whose last_assigned_at
    is the oldest (nulls = never assigned, so they come first).
    """
    return (
        db.query(AgentProfile)
        .join(User, User.id == AgentProfile.user_id)
        .filter(
            AgentProfile.availability_status == "available",
            AgentProfile.active_enquiry_count < AgentProfile.max_concurrent_enquiries,
            User.status == "active",
            User.is_deleted == False,
        )
        .order_by(nullsfirst(asc(AgentProfile.last_assigned_at)))
        .with_for_update(skip_locked=True)  # prevents double-assignment under concurrency
        .first()
    )


def assign_enquiry(enquiry: Enquiry, db: Session) -> AgentProfile | None:
    """
    Try to assign an enquiry to the next available agent.
    Returns the AgentProfile if assignment succeeded, None if no agent is available
    (enquiry remains 'unassigned' in the pending queue).
    """
    agent = _pick_next_agent(db)
    if not agent:
        return None

    _do_assign(agent, enquiry, db)
    return agent


def _do_assign(agent: AgentProfile, enquiry: Enquiry, db: Session) -> None:
    now = datetime.now(timezone.utc)
    enquiry.agent_id = agent.user_id
    enquiry.status = "assigned"
    enquiry.assigned_at = now

    agent.last_assigned_at = now
    agent.active_enquiry_count += 1
    if agent.active_enquiry_count >= agent.max_concurrent_enquiries:
        agent.availability_status = "busy"

    db.flush()

    # Notify Chakra of the assignment (fire-and-forget)
    notify_agent_assigned(
        chakra_enquiry_id=enquiry.chakra_enquiry_id or "",
        agent_id=str(agent.user_id),
        agent_name=agent.user.full_name if agent.user else str(agent.user_id),
    )


def release_enquiry(agent_user_id, db: Session) -> None:
    """
    Called when an enquiry is closed for an agent. Decrements their count,
    flips back to 'available' if below capacity, then drains one item from
    the pending queue.
    """
    agent = (
        db.query(AgentProfile)
        .filter(AgentProfile.user_id == agent_user_id)
        .first()
    )
    if not agent:
        return

    agent.active_enquiry_count = max(0, agent.active_enquiry_count - 1)

    # Only flip to available if they are currently logged in (i.e. not offline)
    if agent.availability_status == "busy":
        agent.availability_status = "available"

    db.flush()

    # Drain one item from the pending queue
    _drain_pending_queue(agent, db)


def _drain_pending_queue(agent: AgentProfile, db: Session) -> None:
    """Assign the oldest unassigned enquiry to this agent if they are still available."""
    if agent.availability_status != "available":
        return

    pending = (
        db.query(Enquiry)
        .filter(Enquiry.status == "unassigned")
        .order_by(asc(Enquiry.created_at))
        .with_for_update(skip_locked=True)
        .first()
    )
    if pending:
        _do_assign(agent, pending, db)


def set_agent_available(agent_user_id, db: Session) -> None:
    """Called on agent login — mark available and drain any pending queue."""
    agent = db.query(AgentProfile).filter(AgentProfile.user_id == agent_user_id).first()
    if not agent:
        return
    agent.availability_status = "available"
    agent.active_enquiry_count = 0
    db.flush()
    _drain_pending_queue(agent, db)


def set_agent_offline(agent_user_id, db: Session) -> None:
    """
    Called on agent logout. Marks them offline and re-queues any enquiries
    that are still 'assigned' to them back to 'unassigned'.
    """
    agent = db.query(AgentProfile).filter(AgentProfile.user_id == agent_user_id).first()
    if not agent:
        return

    agent.availability_status = "offline"
    agent.active_enquiry_count = 0
    db.flush()

    # Re-queue open enquiries assigned to this agent
    open_enquiries = (
        db.query(Enquiry)
        .filter(Enquiry.agent_id == agent_user_id, Enquiry.status == "assigned")
        .all()
    )
    for enq in open_enquiries:
        enq.agent_id = None
        enq.status = "unassigned"
        enq.assigned_at = None

    db.flush()
