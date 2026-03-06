from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.payment import Wallet
from app.models.profile import PartnerProfile
from app.models.user import User
from app.schemas.common import PartnerProfileOut, PartnerUpdateRequest, WalletOut

router = APIRouter(prefix="/partners", tags=["Partners"])


def _get_partner_or_404(partner_id: UUID, db: Session) -> PartnerProfile:
    partner = db.query(PartnerProfile).filter(PartnerProfile.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner


@router.get("", status_code=200)
def list_partners(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    q = db.query(PartnerProfile).join(User, PartnerProfile.user_id == User.id)
    if status:
        q = q.filter(User.status == status)
    if search:
        q = q.filter(
            (PartnerProfile.business_name.ilike(f"%{search}%"))
            | (PartnerProfile.description.ilike(f"%{search}%"))
        )
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [PartnerProfileOut.model_validate(p) for p in items]}


@router.get("/{id}", status_code=200)
def get_partner(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "agent")),
):
    return PartnerProfileOut.model_validate(_get_partner_or_404(id, db))


@router.patch("/{id}", status_code=200)
def update_partner(
    id: UUID,
    body: PartnerUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "agent")),
):
    partner = _get_partner_or_404(id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "status":
            partner.user.status = value
        else:
            setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return PartnerProfileOut.model_validate(partner)


@router.post("/{id}/approve", status_code=200)
def approve_partner(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    partner = _get_partner_or_404(id, db)
    partner.user.status = "active"
    db.commit()
    return {"message": "Partner approved"}


@router.post("/{id}/reject", status_code=200)
def reject_partner(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    partner = _get_partner_or_404(id, db)
    partner.user.status = "rejected"
    db.commit()
    return {"message": "Partner rejected"}


@router.post("/{id}/suspend", status_code=200)
def suspend_partner(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    partner = _get_partner_or_404(id, db)
    partner.user.status = "suspended"
    db.commit()
    return {"message": "Partner suspended"}


@router.get("/{id}/wallet", response_model=WalletOut)
def get_partner_wallet(
    id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    partner = _get_partner_or_404(id, db)
    wallet = db.query(Wallet).filter(Wallet.partner_id == partner.id).first()
    if not wallet:
        return WalletOut(escrowBalance=0, availableBalance=0, pendingBalance=0)
    return WalletOut(
        escrowBalance=float(wallet.escrow_balance),
        availableBalance=float(wallet.available_balance),
        pendingBalance=float(wallet.pending_balance),
    )
