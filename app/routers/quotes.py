from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.quote import Quote
from app.models.user import User
from app.schemas.transactions import QuoteCreate, QuoteOut

router = APIRouter(prefix="/quotes", tags=["Quotes"])


@router.post("", status_code=201)
def create_quote(body: QuoteCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    quote = Quote(
        customer_name=body.customerName,
        customer_phone_number=body.customerPhoneNumber,
        customer_email=body.customerEmail,
        service_title=body.serviceTitle,
        reference_id=body.referenceID,
        contract_id=body.contractID,
        agent_id=body.agentId,
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
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return QuoteOut.model_validate(quote)


@router.get("", status_code=200)
def list_quotes(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    quotes = db.query(Quote).all()
    return [QuoteOut.model_validate(q) for q in quotes]


@router.get("/{id}", status_code=200)
def get_quote(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    quote = db.query(Quote).filter(Quote.id == id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteOut.model_validate(quote)


@router.delete("/{id}", status_code=200)
def delete_quote(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    quote = db.query(Quote).filter(Quote.id == id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    db.delete(quote)
    db.commit()
    return {"message": "Quote deleted"}
