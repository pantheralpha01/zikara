from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.booking import Booking, BookingPartner
from app.models.refund_dispute import Refund
from app.models.user import User
from app.schemas.bookings import BookingCreate, BookingOut, BookingReassign, BookingUpdate

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    status_code=201,
    response_model=BookingOut,
    summary="Create a booking",
    description=(
        "Creates a new booking with `status=pending` and `payment_status=unpaid`. "
        "The booking is automatically moved to `status=confirmed` once a payment is fully confirmed via `POST /payments/{id}/confirm`. "
        "\n\nFlow: Create booking → `POST /payments/initiate` (with bookingId) → client pays on provider → `POST /payments/{id}/confirm` → booking confirmed."
    ),
)
def create_booking(body: BookingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "client" and body.clientId != current_user.id:
        raise HTTPException(status_code=403, detail="Clients can only create their own bookings")
    if current_user.role == "agent" and body.agentId != current_user.id:
        raise HTTPException(status_code=403, detail="Agents can only create bookings assigned to themselves")
    if current_user.role == "partner":
        raise HTTPException(status_code=403, detail="Partners cannot create bookings")

    booking = Booking(
        client_id=body.clientId,
        agent_id=body.agentId,
        contract_id=body.contractId,
        currency=body.currency,
        partners=[p.model_dump(mode='json') for p in body.partners],
        total_amount=body.totalAmount,
        payment_type=body.paymentType,
        cost_at_booking=body.costAtBooking,
        cost_post_event=body.costPostEvent,
        due_date=body.dueDate,
        service_start_at=body.serviceStartAt,
        service_end_at=body.serviceEndAt,
        status="pending",
    )
    db.add(booking)
    db.flush()  # get booking.id before inserting partners
    for p in body.partners:
        db.add(BookingPartner(booking_id=booking.id, partner_id=p.partnerId, amount=p.amount))
    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)


@router.get(
    "/calendar",
    status_code=200,
    summary="Get booking calendar",
    description="Returns a lightweight list of bookings (id, start, end, status) for calendar display. Scoped to the current user's role.",
)
def booking_calendar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Booking.service_start_at, Booking.service_end_at, Booking.id, Booking.status)
    if current_user.role == "client":
        q = q.filter(Booking.client_id == current_user.id)
    elif current_user.role == "agent":
        q = q.filter(Booking.agent_id == current_user.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    bookings = q.all()
    return [{"id": str(b.id), "start": b.service_start_at, "end": b.service_end_at, "status": b.status} for b in bookings]


@router.get(
    "",
    status_code=200,
    summary="List bookings",
    description="Returns a paginated list of bookings. Includes `amount_paid` and `payment_status` so callers can see partial-payment progress.",
)
def list_bookings(
    status: Optional[str] = Query(None),
    agentId: Optional[UUID] = Query(None),
    partnerId: Optional[UUID] = Query(None),
    dateFrom: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Booking)
    if current_user.role == "client":
        q = q.filter(Booking.client_id == current_user.id)
    elif current_user.role == "agent":
        q = q.filter(Booking.agent_id == current_user.id)
    elif current_user.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if status:
        q = q.filter(Booking.status == status)
    if agentId:
        q = q.filter(Booking.agent_id == agentId)
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [BookingOut.model_validate(b) for b in items]}


@router.get(
    "/{id}",
    status_code=200,
    response_model=BookingOut,
    summary="Get a booking",
    description="Fetch a single booking by ID. Response includes `amount_paid` and `payment_status` (`unpaid`, `partially_paid`, `fully_paid`).",
)
def get_booking(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role not in {"admin", "manager"} and booking.client_id != current_user.id and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this booking")

    return BookingOut.model_validate(booking)


@router.patch(
    "/{id}",
    status_code=200,
    response_model=BookingOut,
    summary="Update a booking",
    description="Update booking status or notes. Payment tracking fields (`amount_paid`, `payment_status`) are managed automatically via the payments endpoints.",
)
def update_booking(id: UUID, body: BookingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role not in {"admin", "manager"} and booking.client_id != current_user.id and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to update this booking")

    for field, value in body.model_dump(exclude_none=True).items():
        if hasattr(booking, field):
            setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)


@router.post(
    "/{id}/reassign",
    status_code=200,
    response_model=BookingOut,
    summary="Reassign booking to a different agent",
    description="Reassigns the booking to another agent. Only admin and manager can perform this action — intended for when the original agent is unavailable.",
)
def reassign_booking(
    id: UUID,
    body: BookingReassign,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot reassign a cancelled booking")
    new_agent = db.query(User).filter(User.id == body.agentId, User.role == "agent", User.is_deleted == False).first()
    if not new_agent:
        raise HTTPException(status_code=404, detail="Target agent not found")
    booking.agent_id = body.agentId
    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)


@router.post(
    "/{id}/cancel",
    status_code=200,
    response_model=BookingOut,
    summary="Cancel a booking and initiate refund",
    description=(
        "Cancels the booking and automatically creates a pending refund for the amount already paid. "
        "Client may cancel their own booking; agent may cancel their assigned booking; admin and manager can cancel any booking."
    ),
)
def cancel_booking(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role not in {"admin", "manager"}:
        if booking.client_id != current_user.id and booking.agent_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not allowed to cancel this booking")

    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    if booking.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed booking")

    booking.status = "cancelled"

    # Auto-initiate refund for the amount paid so far
    amount_paid = float(booking.amount_paid or 0)
    if amount_paid > 0:
        refund = Refund(
            booking_id=booking.id,
            amount=amount_paid,
            reason="Booking cancelled",
        )
        db.add(refund)

    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)


@router.delete(
    "/{id}",
    status_code=200,
    summary="Delete a booking",
)
def delete_booking(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role != "admin" and booking.client_id != current_user.id and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to delete this booking")

    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted"}


@router.post(
    "/{id}/complete",
    status_code=200,
    summary="Mark booking as complete",
    description="Agents or admins can mark a confirmed booking as completed. Only callable once the booking exists and is assigned to the requesting agent.",
)
def complete_booking(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_role("agent", "admin"))):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role == "agent" and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only complete your assigned bookings")

    booking.status = "completed"
    db.commit()
    return {"message": "Booking marked complete"}
