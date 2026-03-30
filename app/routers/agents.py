from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_admin_only, require_role
from app.db.session import get_db
from app.models.payment import Wallet
from app.models.profile import AgentProfile
from app.models.user import User
from app.schemas.common import AgentProfileOut

router = APIRouter(prefix="/agents", tags=["Agents"])


def _get_agent_or_404(agent_id: UUID, db: Session) -> AgentProfile:
    agent = db.query(AgentProfile).filter(AgentProfile.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("", status_code=200)
def list_agents(
    status: Optional[str] = Query(None, description="Filter by user status: pending, active, suspended, rejected"),
    search: Optional[str] = Query(None, description="Search by full name (partial match)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    q = db.query(AgentProfile).join(User, AgentProfile.user_id == User.id).options(joinedload(AgentProfile.user))
    if status:
        q = q.filter(User.status == status)
    if search:
        q = q.filter(User.full_name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [AgentProfileOut.model_validate(a) for a in items]}


@router.get("/{id}", status_code=200)
def get_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return AgentProfileOut.model_validate(_get_agent_or_404(id, db))


@router.post("/{id}/approve", status_code=200)
def approve_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_admin_only())):
    agent = _get_agent_or_404(id, db)
    agent.user.status = "active"
    if not db.query(Wallet).filter(Wallet.agent_id == agent.id).first():
        db.add(Wallet(agent_id=agent.id, escrow_balance=0, available_balance=0, pending_balance=0))
    db.commit()
    return {"message": "Agent approved"}


@router.post("/{id}/suspend", status_code=200)
def suspend_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_admin_only())):
    agent = _get_agent_or_404(id, db)
    agent.user.status = "suspended"
    db.commit()
    return {"message": "Agent suspended"}


@router.post("/{id}/reactivate", status_code=200)
def reactivate_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_admin_only())):
    agent = _get_agent_or_404(id, db)
    agent.user.status = "active"
    db.commit()
    return {"message": "Agent reactivated"}
