from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.profile import AgentProfile
from app.models.user import User
from app.schemas.common import AgentProfileOut, AgentSelfOut

router = APIRouter(prefix="/managers", tags=["Managers"])


def _get_manager_or_404(manager_id: UUID, db: Session) -> User:
    user = db.query(User).filter(
        User.id == manager_id,
        User.role == "manager",
        User.is_deleted == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Manager not found")
    return user


def _build_manager_out(user: User, db: Session) -> AgentSelfOut:
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == user.id).first()
    return AgentSelfOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        gender=user.gender,
        profile_pic_url=user.profile_pic_url,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        profile=AgentProfileOut.model_validate(profile) if profile else None,
    )


@router.get("", status_code=200)
def list_managers(
    status: Optional[str] = Query(None, description="Filter by status: active, suspended"),
    search: Optional[str] = Query(None, description="Search by full name (partial match)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    q = db.query(User).filter(User.role == "manager", User.is_deleted == False)
    if status:
        q = q.filter(User.status == status)
    if search:
        q = q.filter(User.full_name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [_build_manager_out(u, db) for u in items]}


@router.get("/{id}", response_model=AgentSelfOut, status_code=200)
def get_manager(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return _build_manager_out(_get_manager_or_404(id, db), db)


@router.post("/{agent_id}/promote", status_code=200)
def promote_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Promote an active agent to manager. Uses the agent's user_id (UUID from the users table)."""
    user = db.query(User).filter(
        User.id == agent_id,
        User.is_deleted == False,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "agent":
        raise HTTPException(status_code=400, detail="User is not an agent")
    if user.status != "active":
        raise HTTPException(status_code=400, detail="Only active agents can be promoted to manager")
    user.role = "manager"
    db.commit()
    return {"message": "Agent promoted to manager"}


@router.post("/{id}/suspend", status_code=200)
def suspend_manager(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    user = _get_manager_or_404(id, db)
    user.status = "suspended"
    user.refresh_token = None
    db.commit()
    return {"message": "Manager suspended"}


@router.post("/{id}/reactivate", status_code=200)
def reactivate_manager(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    user = _get_manager_or_404(id, db)
    user.status = "active"
    db.commit()
    return {"message": "Manager reactivated"}


@router.post("/{id}/revoke", status_code=200)
def revoke_manager(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    """Revoke manager privileges — returns the user back to agent role."""
    user = _get_manager_or_404(id, db)
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Manager has no agent profile — cannot revert to agent role",
        )
    user.role = "agent"
    db.commit()
    return {"message": "Manager revoked — returned to agent role"}
