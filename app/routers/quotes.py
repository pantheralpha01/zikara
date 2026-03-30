from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.quote import Quote
from app.models.user import User
from app.schemas.transactions import QuoteCreate, QuoteOut

router = APIRouter(prefix="/quotes", tags=["Quotes"])


@router.post("", status_code=201)
def create_quote(body: QuoteCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "agent"))):
    agent_id = body.agentId
    if current_user.role == "agent":
        if body.agentId and body.agentId != current_user.id:
            raise HTTPException(status_code=403, detail="Agents can only create quotes for themselves")
        agent_id = current_user.id

    quote = Quote(
        customer_name=body.customerName,
        customer_phone_number=body.customerPhoneNumber,
        customer_email=body.customerEmail,
        service_title=body.serviceTitle,
        reference_id=body.referenceID,
        contract_id=body.contractID,
        agent_id=agent_id,
        currency=body.currency,
        multiple_partners_enabled=str(body.multiplepartnersEnabled).lower(),
        partners=[p.model_dump(mode='json') for p in body.partners],
        total_amount=body.totalAmount,
        payment_type=body.paymentType,
        cost_at_booking=body.costAtBooking,
        cost_post_event=body.costPostEvent,
        pay_post_event_due_date=body.payPostEventDueDate,
        service_start_at=body.serviceStartAt,
        service_end_at=body.serviceEndAt,
        service_timezone=body.serviceTimezone,
        chakra_enquiry_id=body.chakraEnquiryId,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return QuoteOut.model_validate(quote)


@router.get("", status_code=200)
def list_quotes(db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "agent"))):
    q = db.query(Quote)
    if current_user.role == "agent":
        q = q.filter(Quote.agent_id == current_user.id)
    quotes = q.all()
    return [QuoteOut.model_validate(q) for q in quotes]


@router.get("/{id}", status_code=200)
def get_quote(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "agent"))):
    quote = db.query(Quote).filter(Quote.id == id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    if current_user.role == "agent" and quote.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this quote")
    return QuoteOut.model_validate(quote)


@router.delete("/{id}", status_code=200)
def delete_quote(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    quote = db.query(Quote).filter(Quote.id == id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    db.delete(quote)
    db.commit()
    return {"message": "Quote deleted"}
