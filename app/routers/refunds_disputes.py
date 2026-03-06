from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.refund_dispute import Dispute, Refund
from app.models.user import User
from app.schemas.bookings import (
    DisputeCreate,
    DisputeOut,
    DisputeUpdate,
    RefundCreate,
    RefundOut,
    RefundUpdate,
)

refunds_router = APIRouter(prefix="/refunds", tags=["Refunds"])
disputes_router = APIRouter(prefix="/disputes", tags=["Disputes"])


# ── Refunds ───────────────────────────────────────────────────────────────────

@refunds_router.post("", status_code=201)
def create_refund(body: RefundCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refund = Refund(booking_id=body.bookingId, amount=body.amount, reason=body.reason)
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return RefundOut.model_validate(refund)


@refunds_router.get("", status_code=200)
def list_refunds(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [RefundOut.model_validate(r) for r in db.query(Refund).all()]


@refunds_router.get("/{id}", status_code=200)
def get_refund(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refund = db.query(Refund).filter(Refund.id == id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return RefundOut.model_validate(refund)


@refunds_router.patch("/{id}", status_code=200)
def update_refund(id: UUID, body: RefundUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refund = db.query(Refund).filter(Refund.id == id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(refund, field, value)
    db.commit()
    db.refresh(refund)
    return RefundOut.model_validate(refund)


@refunds_router.delete("/{id}", status_code=200)
def delete_refund(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refund = db.query(Refund).filter(Refund.id == id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    db.delete(refund)
    db.commit()
    return {"message": "Refund deleted"}


# ── Disputes ──────────────────────────────────────────────────────────────────

@disputes_router.post("", status_code=201)
def create_dispute(body: DisputeCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dispute = Dispute(booking_id=body.bookingId, reason=body.reason, description=body.description)
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return DisputeOut.model_validate(dispute)


@disputes_router.get("", status_code=200)
def list_disputes(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [DisputeOut.model_validate(d) for d in db.query(Dispute).all()]


@disputes_router.get("/{id}", status_code=200)
def get_dispute(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dispute = db.query(Dispute).filter(Dispute.id == id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return DisputeOut.model_validate(dispute)


@disputes_router.patch("/{id}", status_code=200)
def update_dispute(id: UUID, body: DisputeUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dispute = db.query(Dispute).filter(Dispute.id == id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(dispute, field, value)
    db.commit()
    db.refresh(dispute)
    return DisputeOut.model_validate(dispute)


@disputes_router.delete("/{id}", status_code=200)
def delete_dispute(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dispute = db.query(Dispute).filter(Dispute.id == id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    db.delete(dispute)
    db.commit()
    return {"message": "Dispute deleted"}
