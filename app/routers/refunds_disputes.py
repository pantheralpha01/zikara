from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.models.booking import Booking
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


def _get_booking_or_404(booking_id: UUID, db: Session) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


def _require_booking_access(booking: Booking, current_user: User):
    if current_user.role == "admin":
        return
    if current_user.role == "client" and booking.client_id == current_user.id:
        return
    if current_user.role == "agent" and booking.agent_id == current_user.id:
        return
    raise HTTPException(status_code=403, detail="You are not allowed to access this booking")


# ── Refunds ───────────────────────────────────────────────────────────────────

@refunds_router.post("", status_code=201)
def create_refund(body: RefundCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = _get_booking_or_404(body.bookingId, db)
    _require_booking_access(booking, current_user)
    refund = Refund(booking_id=body.bookingId, amount=body.amount, reason=body.reason)
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return RefundOut.model_validate(refund)


@refunds_router.get("", status_code=200)
def list_refunds(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Refund)
    if current_user.role == "client":
        q = q.join(Booking, Refund.booking_id == Booking.id).filter(Booking.client_id == current_user.id)
    elif current_user.role == "agent":
        q = q.join(Booking, Refund.booking_id == Booking.id).filter(Booking.agent_id == current_user.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [RefundOut.model_validate(r) for r in q.all()]


@refunds_router.get("/{id}", status_code=200)
def get_refund(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    refund = db.query(Refund).filter(Refund.id == id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    booking = _get_booking_or_404(refund.booking_id, db)
    _require_booking_access(booking, current_user)
    return RefundOut.model_validate(refund)


@refunds_router.patch("/{id}", status_code=200)
def update_refund(id: UUID, body: RefundUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    refund = db.query(Refund).filter(Refund.id == id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    if current_user.role not in {"admin", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    booking = _get_booking_or_404(refund.booking_id, db)
    if current_user.role == "agent" and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to update this refund")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(refund, field, value)
    db.commit()
    db.refresh(refund)
    return RefundOut.model_validate(refund)


@refunds_router.delete("/{id}", status_code=200)
def delete_refund(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    refund = db.query(Refund).filter(Refund.id == id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    db.delete(refund)
    db.commit()
    return {"message": "Refund deleted"}


# ── Disputes ──────────────────────────────────────────────────────────────────

@disputes_router.post("", status_code=201)
def create_dispute(body: DisputeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = _get_booking_or_404(body.bookingId, db)
    _require_booking_access(booking, current_user)
    dispute = Dispute(booking_id=body.bookingId, reason=body.reason, description=body.description)
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return DisputeOut.model_validate(dispute)


@disputes_router.get("", status_code=200)
def list_disputes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Dispute)
    if current_user.role == "client":
        q = q.join(Booking, Dispute.booking_id == Booking.id).filter(Booking.client_id == current_user.id)
    elif current_user.role == "agent":
        q = q.join(Booking, Dispute.booking_id == Booking.id).filter(Booking.agent_id == current_user.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [DisputeOut.model_validate(d) for d in q.all()]


@disputes_router.get("/{id}", status_code=200)
def get_dispute(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dispute = db.query(Dispute).filter(Dispute.id == id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    booking = _get_booking_or_404(dispute.booking_id, db)
    _require_booking_access(booking, current_user)
    return DisputeOut.model_validate(dispute)


@disputes_router.patch("/{id}", status_code=200)
def update_dispute(id: UUID, body: DisputeUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dispute = db.query(Dispute).filter(Dispute.id == id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if current_user.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(dispute, field, value)
    db.commit()
    db.refresh(dispute)
    return DisputeOut.model_validate(dispute)


@disputes_router.delete("/{id}", status_code=200)
def delete_dispute(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    dispute = db.query(Dispute).filter(Dispute.id == id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    db.delete(dispute)
    db.commit()
    return {"message": "Dispute deleted"}
