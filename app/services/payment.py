from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.payment import Wallet, WalletTransaction


def _get_or_create_wallet(db: Session, *, agent_id: Optional[str] = None, partner_id: Optional[str] = None) -> Wallet:
    if agent_id is not None:
        wallet = db.query(Wallet).filter(Wallet.agent_id == agent_id).first()
        if not wallet:
            wallet = Wallet(agent_id=agent_id, escrow_balance=0, available_balance=0, pending_balance=0)
            db.add(wallet)
            db.flush()
        return wallet

    if partner_id is not None:
        wallet = db.query(Wallet).filter(Wallet.partner_id == partner_id).first()
        if not wallet:
            wallet = Wallet(partner_id=partner_id, escrow_balance=0, available_balance=0, pending_balance=0)
            db.add(wallet)
            db.flush()
        return wallet

    raise ValueError("agent_id or partner_id must be provided")


def _compute_wallet_shares(booking: Booking, amount: float) -> Tuple[float, list[tuple[str, float]]]:
    amount = float(amount)
    if amount <= 0:
        return 0.0, []

    total_amount = float(booking.total_amount or 0)
    partner_shares: list[tuple[str, float]] = []
    if total_amount > 0 and booking.booking_partners:
        for partner in booking.booking_partners:
            share = round(amount * float(partner.amount or 0) / total_amount, 2)
            partner_shares.append((str(partner.partner_id), share))
        agent_share = round(amount - sum(share for _, share in partner_shares), 2)
    else:
        partner_shares = []
        agent_share = amount

    return agent_share, partner_shares


def allocate_payment_to_wallets(db: Session, booking: Booking, amount: float, reference: Optional[str] = None) -> None:
    agent_share, partner_shares = _compute_wallet_shares(booking, amount)

    if agent_share:
        agent_wallet = _get_or_create_wallet(db, agent_id=str(booking.agent_id))
        agent_wallet.escrow_balance = float(agent_wallet.escrow_balance or 0) + agent_share
        db.add(
            WalletTransaction(
                wallet_id=agent_wallet.id,
                type="escrow_in",
                amount=agent_share,
                reference=reference,
            )
        )

    for partner_id, partner_amount in partner_shares:
        if partner_amount:
            partner_wallet = _get_or_create_wallet(db, partner_id=partner_id)
            partner_wallet.escrow_balance = float(partner_wallet.escrow_balance or 0) + partner_amount
            db.add(
                WalletTransaction(
                    wallet_id=partner_wallet.id,
                    type="escrow_in",
                    amount=partner_amount,
                    reference=reference,
                )
            )


def release_booking_wallets(db: Session, booking: Booking, reference: Optional[str] = None) -> None:
    agent_wallet = _get_or_create_wallet(db, agent_id=str(booking.agent_id))
    agent_escrow = float(agent_wallet.escrow_balance or 0)
    if agent_escrow > 0:
        agent_wallet.available_balance = float(agent_wallet.available_balance or 0) + agent_escrow
        agent_wallet.escrow_balance = 0
        db.add(
            WalletTransaction(
                wallet_id=agent_wallet.id,
                type="escrow_release",
                amount=agent_escrow,
                reference=reference,
            )
        )

    for partner in booking.booking_partners:
        partner_wallet = _get_or_create_wallet(db, partner_id=str(partner.partner_id))
        partner_escrow = float(partner_wallet.escrow_balance or 0)
        if partner_escrow > 0:
            partner_wallet.available_balance = float(partner_wallet.available_balance or 0) + partner_escrow
            partner_wallet.escrow_balance = 0
            db.add(
                WalletTransaction(
                    wallet_id=partner_wallet.id,
                    type="escrow_release",
                    amount=partner_escrow,
                    reference=reference,
                )
            )


def debit_wallets_for_refund(db: Session, booking: Booking, amount: float, reference: Optional[str] = None) -> None:
    agent_share, partner_shares = _compute_wallet_shares(booking, amount)

    def _debit(wallet: Wallet, debit: float) -> None:
        debit = float(debit)
        available = float(wallet.available_balance or 0)
        if available >= debit:
            wallet.available_balance = available - debit
        else:
            wallet.available_balance = 0
            wallet.escrow_balance = float(wallet.escrow_balance or 0) - (debit - available)

    if agent_share:
        agent_wallet = _get_or_create_wallet(db, agent_id=str(booking.agent_id))
        _debit(agent_wallet, agent_share)
        db.add(
            WalletTransaction(
                wallet_id=agent_wallet.id,
                type="refund_debit",
                amount=agent_share,
                reference=reference,
            )
        )

    for partner_id, partner_amount in partner_shares:
        if partner_amount:
            partner_wallet = _get_or_create_wallet(db, partner_id=partner_id)
            _debit(partner_wallet, partner_amount)
            db.add(
                WalletTransaction(
                    wallet_id=partner_wallet.id,
                    type="refund_debit",
                    amount=partner_amount,
                    reference=reference,
                )
            )
