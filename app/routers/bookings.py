from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.booking import Booking
from app.models.user import User
from app.schemas.bookings import BookingCreate, BookingOut, BookingUpdate

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", status_code=201)
def create_booking(body: BookingCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    booking = Booking(
        client_id=body.clientId,
        agent_id=body.agentId,
        contract_id=body.contractId,
        payment_id=body.paymentId,
        currency=body.currency,
        partners=[p.model_dump(mode='json') for p in body.partners],
        total_amount=body.totalAmount,
        payment_type=body.paymentType,
        cost_at_booking=body.costAtBooking,
        cost_post_event=body.costPostEvent,
        due_date=body.dueDate,
        service_start_at=body.serviceStartAt,
        service_end_at=body.serviceEndAt,
        status=body.status,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)


@router.get("/calendar", status_code=200)
def booking_calendar(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    bookings = db.query(Booking.service_start_at, Booking.service_end_at, Booking.id, Booking.status).all()
    return [{"id": str(b.id), "start": b.service_start_at, "end": b.service_end_at, "status": b.status} for b in bookings]


@router.get("", status_code=200)
def list_bookings(
    status: Optional[str] = Query(None),
    agentId: Optional[UUID] = Query(None),
    partnerId: Optional[UUID] = Query(None),
    dateFrom: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Booking)
    if status:
        q = q.filter(Booking.status == status)
    if agentId:
        q = q.filter(Booking.agent_id == agentId)
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [BookingOut.model_validate(b) for b in items]}


@router.get("/{id}", status_code=200)
def get_booking(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingOut.model_validate(booking)


@router.patch("/{id}", status_code=200)
def update_booking(id: UUID, body: BookingUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    for field, value in body.model_dump(exclude_none=True).items():
        if hasattr(booking, field):
            setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)


@router.delete("/{id}", status_code=200)
def delete_booking(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted"}


@router.post("/{id}/complete", status_code=200)
def complete_booking(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("agent"))):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "completed"
    db.commit()
    return {"message": "Booking marked complete"}
