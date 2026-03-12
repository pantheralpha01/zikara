from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.booking import Booking
from app.models.payment import Payment, Wallet
from app.models.profile import PartnerProfile
from app.models.user import User
from app.schemas.bookings import PaymentInitiate, PaymentOut, WithdrawRequest

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initiate", status_code=200)
def initiate_payment(body: PaymentInitiate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == body.bookingId).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role == "client" and booking.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Clients can only initiate payments for their own bookings")
    if current_user.role == "agent" and booking.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Agents can only initiate payments for assigned bookings")
    if current_user.role not in {"admin", "client", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    payment = Payment(
        booking_id=body.bookingId,
        amount=body.amount,
        currency=body.currency,
        provider=body.provider,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PaymentOut.model_validate(payment)


@router.post("/webhook/{provider}", status_code=200, include_in_schema=False)
async def payment_webhook(provider: str, request: Request, db: Session = Depends(get_db)):
    # Providers send raw bodies; this is a hook for handling payment events.
    # Validate webhook signatures here using provider-specific logic before trusting payload.
    body = await request.json()
    # Minimal stub: log and acknowledge
    return {"received": True, "provider": provider}


@router.get("/list", status_code=200)
def list_payments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Payment)
    if current_user.role == "client":
        q = q.join(Booking, Payment.booking_id == Booking.id).filter(Booking.client_id == current_user.id)
    elif current_user.role == "agent":
        q = q.join(Booking, Payment.booking_id == Booking.id).filter(Booking.agent_id == current_user.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    payments = q.all()
    return [PaymentOut.model_validate(p) for p in payments]


@router.get("/{id}", status_code=200)
def get_payment(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if current_user.role != "admin":
        booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if current_user.role == "client" and booking.client_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not allowed to view this payment")
        if current_user.role == "agent" and booking.agent_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not allowed to view this payment")
        if current_user.role not in {"client", "agent"}:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    return PaymentOut.model_validate(payment)


# ── Wallets ───────────────────────────────────────────────────────────────────

wallet_router = APIRouter(prefix="/wallets", tags=["Wallets"])


@wallet_router.get("/{partnerId}", status_code=200)
def get_wallet(partnerId: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        if current_user.role != "partner":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
        if not partner_profile or partner_profile.id != partnerId:
            raise HTTPException(status_code=403, detail="You can only view your own wallet")

    wallet = db.query(Wallet).filter(Wallet.partner_id == partnerId).first()
    if not wallet:
        return {"escrowBalance": 0, "availableBalance": 0}
    return {"escrowBalance": float(wallet.escrow_balance), "availableBalance": float(wallet.available_balance)}


@wallet_router.post("/{partnerId}/withdraw", status_code=200)
def withdraw(partnerId: UUID, body: WithdrawRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        if current_user.role != "partner":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
        if not partner_profile or partner_profile.id != partnerId:
            raise HTTPException(status_code=403, detail="You can only withdraw from your own wallet")

    wallet = db.query(Wallet).filter(Wallet.partner_id == partnerId).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if wallet.available_balance < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    wallet.available_balance = float(wallet.available_balance) - body.amount
    db.commit()
    return {"message": "Withdrawal processed", "remainingBalance": float(wallet.available_balance)}
