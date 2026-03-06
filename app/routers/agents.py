from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
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
def list_agents(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    agents = db.query(AgentProfile).all()
    return [AgentProfileOut.model_validate(a) for a in agents]


@router.get("/{id}", status_code=200)
def get_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return AgentProfileOut.model_validate(_get_agent_or_404(id, db))


@router.post("/{id}/approve", status_code=200)
def approve_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    agent = _get_agent_or_404(id, db)
    agent.user.status = "active"
    db.commit()
    return {"message": "Agent approved"}


@router.post("/{id}/suspend", status_code=200)
def suspend_agent(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    agent = _get_agent_or_404(id, db)
    agent.user.status = "suspended"
    db.commit()
    return {"message": "Agent suspended"}
