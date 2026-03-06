from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.listing import Listing
from app.models.user import User
from app.schemas.common import ListingCreate, ListingOut

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.post("", status_code=201)
def create_listing(
    body: ListingCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("partner")),
):
    listing = Listing(
        partner_id=body.partnerId,
        category_id=body.categoryId,
        service_id=body.serviceId,
        title=body.title,
        description=body.description,
        city=body.city,
        country=body.country,
        price_from=body.priceFrom,
        pricing_type=body.pricingType,
        currency=body.currency,
        attributes=body.attributes or {},
        status="pending",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return ListingOut.model_validate(listing)


@router.get("", status_code=200)
def list_listings(
    categoryId: Optional[UUID] = Query(None),
    city: Optional[str] = Query(None),
    minPrice: Optional[float] = Query(None),
    maxPrice: Optional[float] = Query(None),
    partnerId: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Listing)
    if categoryId:
        q = q.filter(Listing.category_id == categoryId)
    if city:
        q = q.filter(Listing.city.ilike(f"%{city}%"))
    if minPrice is not None:
        q = q.filter(Listing.price_from >= minPrice)
    if maxPrice is not None:
        q = q.filter(Listing.price_from <= maxPrice)
    if partnerId:
        q = q.filter(Listing.partner_id == partnerId)
    if status:
        q = q.filter(Listing.status == status)

    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [ListingOut.model_validate(l) for l in items]}


@router.post("/{id}/approve", status_code=200)
def approve_listing(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "approved"
    db.commit()
    return {"message": "Listing approved"}


@router.post("/{id}/reject", status_code=200)
def reject_listing(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "rejected"
    db.commit()
    return {"message": "Listing rejected"}
