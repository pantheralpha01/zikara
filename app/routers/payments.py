from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.booking import Booking
from app.models.payment import Payment, Wallet, WalletTransaction, WithdrawalRequest
from app.models.profile import AgentProfile, PartnerProfile
from app.models.user import User
from app.schemas.bookings import PaymentConfirm, PaymentInitiate, PaymentOut, WithdrawRequest
from app.schemas.common import WalletTransactionOut, WithdrawalRequestOut
from app.core.config import settings
from app.services.email import (
    send_withdrawal_request_alert_email,
    send_withdrawal_request_status_email,
    send_withdrawal_request_submitted_email,
)
from app.services.payment import allocate_payment_to_wallets

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

    allocate_payment_to_wallets(db, booking, float(payment.amount), reference=f"payment:{payment.id}")
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
def withdraw(
    partnerId: UUID,
    body: WithdrawRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    # For large withdrawals (>1000), require admin approval
    LARGE_WITHDRAWAL_THRESHOLD = 1000.0
    if body.amount > LARGE_WITHDRAWAL_THRESHOLD and current_user.role != "admin":
        # Create pending withdrawal request
        withdrawal_request = WithdrawalRequest(
            wallet_id=wallet.id,
            amount=body.amount,
            requested_by=current_user.id,
        )
        db.add(withdrawal_request)
        db.commit()
        db.refresh(withdrawal_request)

        if current_user.email:
            background_tasks.add_task(
                send_withdrawal_request_submitted_email,
                current_user.email,
                current_user.full_name or current_user.email,
                float(body.amount),
                str(withdrawal_request.id),
                "partner",
            )

        if settings.ADMIN_NOTIFICATION_EMAILS:
            background_tasks.add_task(
                send_withdrawal_request_alert_email,
                settings.ADMIN_NOTIFICATION_EMAILS,
                current_user.full_name or current_user.email,
                float(body.amount),
                str(withdrawal_request.id),
                "partner",
            )

        return {"message": "Withdrawal request submitted for approval", "requestId": withdrawal_request.id}
    else:
        # Process immediate withdrawal
        wallet.available_balance = float(wallet.available_balance) - body.amount
        db.add(WalletTransaction(wallet_id=wallet.id, type="payout", amount=body.amount))
        db.commit()
        return {"message": "Withdrawal processed", "remainingBalance": float(wallet.available_balance)}


@wallet_router.get("/{partnerId}/transactions", response_model=list[WalletTransactionOut], status_code=200)
def get_partner_wallet_transactions(partnerId: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        if current_user.role != "partner":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
        if not partner_profile or partner_profile.id != partnerId:
            raise HTTPException(status_code=403, detail="You can only view your own wallet transactions")

    wallet = db.query(Wallet).filter(Wallet.partner_id == partnerId).first()
    if not wallet:
        return []
    return [WalletTransactionOut.model_validate(tx) for tx in wallet.transactions]


@wallet_router.get("/agents/{agentId}", status_code=200)
def get_agent_wallet(agentId: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        if current_user.role != "agent":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        agent_profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
        if not agent_profile or agent_profile.id != agentId:
            raise HTTPException(status_code=403, detail="You can only view your own wallet")

    wallet = db.query(Wallet).filter(Wallet.agent_id == agentId).first()
    if not wallet:
        return {"escrowBalance": 0, "availableBalance": 0, "pendingBalance": 0}
    return {"escrowBalance": float(wallet.escrow_balance), "availableBalance": float(wallet.available_balance), "pendingBalance": float(wallet.pending_balance)}


@wallet_router.get("/agents/{agentId}/transactions", response_model=list[WalletTransactionOut], status_code=200)
def get_agent_wallet_transactions(agentId: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        if current_user.role != "agent":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        agent_profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
        if not agent_profile or agent_profile.id != agentId:
            raise HTTPException(status_code=403, detail="You can only view your own wallet transactions")

    wallet = db.query(Wallet).filter(Wallet.agent_id == agentId).first()
    if not wallet:
        return []
    return [WalletTransactionOut.model_validate(tx) for tx in wallet.transactions]


@wallet_router.post("/agents/{agentId}/withdraw", status_code=200)
def withdraw_agent_wallet(
    agentId: UUID,
    body: WithdrawRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        if current_user.role != "agent":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        agent_profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
        if not agent_profile or agent_profile.id != agentId:
            raise HTTPException(status_code=403, detail="You can only withdraw from your own wallet")

    wallet = db.query(Wallet).filter(Wallet.agent_id == agentId).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if wallet.available_balance < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # For large withdrawals (>1000), require admin approval
    LARGE_WITHDRAWAL_THRESHOLD = 1000.0
    if body.amount > LARGE_WITHDRAWAL_THRESHOLD and current_user.role != "admin":
        # Create pending withdrawal request
        withdrawal_request = WithdrawalRequest(
            wallet_id=wallet.id,
            amount=body.amount,
            requested_by=current_user.id,
        )
        db.add(withdrawal_request)
        db.commit()
        db.refresh(withdrawal_request)

        if current_user.email:
            background_tasks.add_task(
                send_withdrawal_request_submitted_email,
                current_user.email,
                current_user.full_name or current_user.email,
                float(body.amount),
                str(withdrawal_request.id),
                "agent",
            )

        if settings.ADMIN_NOTIFICATION_EMAILS:
            background_tasks.add_task(
                send_withdrawal_request_alert_email,
                settings.ADMIN_NOTIFICATION_EMAILS,
                current_user.full_name or current_user.email,
                float(body.amount),
                str(withdrawal_request.id),
                "agent",
            )

        return {"message": "Withdrawal request submitted for approval", "requestId": withdrawal_request.id}
    else:
        # Process immediate withdrawal
        wallet.available_balance = float(wallet.available_balance) - body.amount
        db.add(WalletTransaction(wallet_id=wallet.id, type="payout", amount=body.amount))
        db.commit()
        return {"message": "Withdrawal processed", "remainingBalance": float(wallet.available_balance)}


# Admin-only withdrawal request management
@router.get("/withdrawal-requests", response_model=list[WithdrawalRequestOut], status_code=200)
def list_withdrawal_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    requests = db.query(WithdrawalRequest).all()
    return [WithdrawalRequestOut.model_validate(req) for req in requests]


@router.post("/withdrawal-requests/{requestId}/approve", status_code=200)
def approve_withdrawal_request(
    requestId: UUID,
    review_note: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    request = db.query(WithdrawalRequest).filter(WithdrawalRequest.id == requestId).first()
    if not request:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request has already been processed")
    
    # Process the withdrawal
    wallet = request.wallet
    if wallet.available_balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    wallet.available_balance = float(wallet.available_balance) - request.amount
    request.status = "approved"
    request.reviewed_by = current_user.id
    request.review_note = review_note
    request.reviewed_at = datetime.now(timezone.utc)
    
    db.add(WalletTransaction(wallet_id=wallet.id, type="payout", amount=request.amount, reference=f"Approved withdrawal request {requestId}"))
    db.commit()

    if request.requester and request.requester.email and background_tasks is not None:
        background_tasks.add_task(
            send_withdrawal_request_status_email,
            request.requester.email,
            request.requester.full_name or request.requester.email,
            float(request.amount),
            str(request.id),
            True,
            review_note,
        )

    return {"message": "Withdrawal request approved and processed"}


@router.post("/withdrawal-requests/{requestId}/reject", status_code=200)
def reject_withdrawal_request(
    requestId: UUID,
    review_note: str,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    request = db.query(WithdrawalRequest).filter(WithdrawalRequest.id == requestId).first()
    if not request:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request has already been processed")
    
    request.status = "rejected"
    request.reviewed_by = current_user.id
    request.review_note = review_note
    request.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    if request.requester and request.requester.email and background_tasks is not None:
        background_tasks.add_task(
            send_withdrawal_request_status_email,
            request.requester.email,
            request.requester.full_name or request.requester.email,
            float(request.amount),
            str(request.id),
            False,
            review_note,
        )

    return {"message": "Withdrawal request rejected"}
