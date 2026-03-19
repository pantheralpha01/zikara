from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.booking import Booking
from app.models.payment import Payment, Wallet
from app.models.profile import PartnerProfile
from app.models.user import User
from app.schemas.bookings import PaymentConfirm, PaymentInitiate, PaymentOut, WithdrawRequest

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/initiate",
    status_code=200,
    response_model=PaymentOut,
    summary="Initiate a payment for a booking",
    description=(
        "Creates a **pending** payment record for a booking. "
        "Supports **partial payments** — `amount` may be less than the booking's `totalAmount`. "
        "The amount must be positive and cannot exceed the remaining unpaid balance. "
        "Call `POST /payments/{id}/confirm` once the provider confirms the charge."
    ),
    response_description="The created pending payment",
)
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

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")

    total = float(booking.total_amount or 0)
    already_paid = float(booking.amount_paid or 0)
    remaining = total - already_paid
    if total > 0 and body.amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds remaining balance. Remaining: {remaining} {booking.currency}",
        )

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


@router.post(
    "/{id}/confirm",
    status_code=200,
    response_model=PaymentOut,
    summary="Confirm a pending payment",
    description=(
        "Marks a **pending** payment as `success` and adds its amount to `booking.amount_paid`. "
        "The booking's `payment_status` is automatically updated: \n\n"
        "- `partially_paid` — if the cumulative paid amount is less than `totalAmount` \n"
        "- `fully_paid` — if the full amount has been settled \n\n"
        "Pass the optional `providerReference` to store the external transaction ID."
    ),
    response_description="The confirmed payment record",
)
def confirm_payment(
    id: UUID,
    body: PaymentConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Payment is not in a pending state")

    booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role not in {"admin"}:
        if current_user.role == "client" and booking.client_id != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        elif current_user.role == "agent" and booking.agent_id != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        elif current_user.role not in {"client", "agent"}:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    if body.providerReference:
        payment.provider_reference = body.providerReference
    payment.status = "success"

    new_amount_paid = float(booking.amount_paid or 0) + float(payment.amount)
    booking.amount_paid = new_amount_paid
    total = float(booking.total_amount or 0)
    if total > 0 and new_amount_paid >= total:
        booking.payment_status = "fully_paid"
        # Auto-confirm the booking once fully paid
        if booking.status == "pending":
            booking.status = "confirmed"
    elif new_amount_paid > 0:
        booking.payment_status = "partially_paid"

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


@router.get(
    "/list",
    status_code=200,
    response_model=list[PaymentOut],
    summary="List payments",
    description="Returns all payments visible to the current user. Clients see only their booking payments; agents see payments for their assigned bookings; admins see all.",
)
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


@router.get(
    "/{id}",
    status_code=200,
    response_model=PaymentOut,
    summary="Get a payment by ID",
)
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
    db.add(WalletTransaction(wallet_id=wallet.id, type="payout", amount=body.amount))
    db.commit()
    return {"message": "Withdrawal processed", "remainingBalance": float(wallet.available_balance)}
