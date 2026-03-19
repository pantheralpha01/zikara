from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.listing import Listing
from app.models.profile import PartnerProfile
from app.models.user import User
from app.schemas.common import ListingCreate, ListingOut

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.post("", status_code=201)
def create_listing(
    body: ListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("partner")),
):
    partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
    if not partner:
        raise HTTPException(status_code=403, detail="Partner profile not found")
    if body.partnerId != partner.id:
        raise HTTPException(status_code=403, detail="You can only create listings for your own partner profile")

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
        images=body.images or [],
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
    current_user: User = Depends(get_current_user),
):
    q = db.query(Listing)
    if current_user.role == "partner":
        partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
        if not partner:
            raise HTTPException(status_code=403, detail="Partner profile not found")
        q = q.filter(Listing.partner_id == partner.id)
    elif current_user.role != "admin":
        q = q.filter(Listing.status == "approved")

    if categoryId:
        q = q.filter(Listing.category_id == categoryId)
    if city:
        q = q.filter(Listing.city.ilike(f"%{city}%"))
    if minPrice is not None:
        q = q.filter(Listing.price_from >= minPrice)
    if maxPrice is not None:
        q = q.filter(Listing.price_from <= maxPrice)
    if partnerId and current_user.role == "admin":
        q = q.filter(Listing.partner_id == partnerId)
    if status:
        q = q.filter(Listing.status == status)

    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [ListingOut.model_validate(l) for l in items]}


@router.post("/{id}/approve", status_code=200)
def approve_listing(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin", "manager"))):
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
