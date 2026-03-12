from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.booking import Booking
from app.models.review import Review
from app.models.user import User
from app.schemas.bookings import ReviewCreate, ReviewOut

router = APIRouter(prefix="/bookings", tags=["Reviews"])


@router.post("/{id}/reviews", status_code=201)
def create_review(
    id: UUID,
    body: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role != "admin" and booking.client_id != current_user.id and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to review this booking")
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed bookings")
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review = Review(booking_id=id, reviewer_id=current_user.id, rating=body.rating, comment=body.comment)
    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)


@router.get("/{id}/reviews", status_code=200)
def list_reviews(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "client", "agent"))):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role != "admin" and booking.client_id != current_user.id and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to view reviews for this booking")
    reviews = db.query(Review).filter(Review.booking_id == id).all()
    return [ReviewOut.model_validate(r) for r in reviews]
