from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.enquiry import Enquiry
from app.models.user import User
from app.schemas.enquiries import EnquiryAssignResponse, EnquiryCreateRequest, EnquiryOut
from app.services.assignment import assign_enquiry, release_enquiry

router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


def _verify_chakra_key(x_chakra_api_key: str = Header(...)):
    """Guard for endpoints called by Chakra HQ. Validates the shared API key."""
    if x_chakra_api_key != settings.CHAKRA_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Chakra API key")


def _enquiry_to_out(enq: Enquiry, db: Session) -> EnquiryOut:
    agent_name = None
    if enq.agent_id:
        agent = db.query(User).filter(User.id == enq.agent_id).first()
        if agent:
            agent_name = agent.full_name
    return EnquiryOut(
        id=enq.id,
        chakra_enquiry_id=enq.chakra_enquiry_id,
        agent_id=enq.agent_id,
        agent_name=agent_name,
        status=enq.status,
        title=enq.title,
        notes=enq.notes,
        customer_name=enq.customer_name,
        customer_email=enq.customer_email,
        customer_phone=enq.customer_phone,
        created_at=enq.created_at,
        assigned_at=enq.assigned_at,
        closed_at=enq.closed_at,
    )


@router.post(
    "",
    response_model=EnquiryAssignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Chakra HQ: Submit a new enquiry for round-robin assignment",
    dependencies=[Depends(_verify_chakra_key)],
)
def create_and_assign_enquiry(body: EnquiryCreateRequest, db: Session = Depends(get_db)):
    """
    Called by Chakra HQ when a new customer enquiry arrives.
    Automatically assigns it to the next available agent via round-robin.
    If no agent is available, the enquiry is queued as 'unassigned'.
    """
    # Prevent duplicate creation if Chakra retries the same event
    if body.chakra_enquiry_id:
        existing = db.query(Enquiry).filter(Enquiry.chakra_enquiry_id == body.chakra_enquiry_id).first()
        if existing:
            return EnquiryAssignResponse(
                enquiry=_enquiry_to_out(existing, db),
                assigned=existing.status == "assigned",
                message="Enquiry already exists",
            )

    enquiry = Enquiry(
        chakra_enquiry_id=body.chakra_enquiry_id,
        title=body.title,
        notes=body.notes,
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
        status="unassigned",
    )
    db.add(enquiry)
    db.flush()

    agent = assign_enquiry(enquiry, db)
    db.commit()
    db.refresh(enquiry)

    if agent:
        return EnquiryAssignResponse(
            enquiry=_enquiry_to_out(enquiry, db),
            assigned=True,
            message=f"Assigned to agent {agent.user.full_name}",
        )
    return EnquiryAssignResponse(
        enquiry=_enquiry_to_out(enquiry, db),
        assigned=False,
        message="No agents available. Enquiry queued.",
    )


@router.post(
    "/{enquiry_id}/close",
    response_model=EnquiryOut,
    summary="Chakra HQ: Mark an enquiry as closed",
    dependencies=[Depends(_verify_chakra_key)],
)
def close_enquiry(enquiry_id: UUID, db: Session = Depends(get_db)):
    """
    Called by Chakra HQ when an enquiry is resolved/closed.
    Releases the agent's slot and auto-assigns the next pending enquiry if any.
    """
    from datetime import datetime, timezone

    enquiry = db.query(Enquiry).filter(Enquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if enquiry.status == "closed":
        return _enquiry_to_out(enquiry, db)

    previously_assigned_agent = enquiry.agent_id
    enquiry.status = "closed"
    enquiry.closed_at = datetime.now(timezone.utc)
    db.flush()

    if previously_assigned_agent:
        release_enquiry(previously_assigned_agent, db)

    db.commit()
    db.refresh(enquiry)
    return _enquiry_to_out(enquiry, db)


@router.get(
    "",
    response_model=List[EnquiryOut],
    summary="List enquiries (admin/manager/agent)",
)
def list_enquiries(
    status_filter: Optional[str] = Query(None, alias="status"),
    agent_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "agent")),
):
    q = db.query(Enquiry)

    # Agents can only see their own enquiries
    if current_user.role == "agent":
        q = q.filter(Enquiry.agent_id == current_user.id)
    elif agent_id:
        q = q.filter(Enquiry.agent_id == agent_id)

    if status_filter:
        q = q.filter(Enquiry.status == status_filter)

    enquiries = q.order_by(Enquiry.created_at.desc()).offset(skip).limit(limit).all()
    return [_enquiry_to_out(e, db) for e in enquiries]


@router.get(
    "/{enquiry_id}",
    response_model=EnquiryOut,
    summary="Get single enquiry",
)
def get_enquiry(
    enquiry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "agent")),
):
    enquiry = db.query(Enquiry).filter(Enquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if current_user.role == "agent" and enquiry.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _enquiry_to_out(enquiry, db)
