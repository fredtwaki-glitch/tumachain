"""
Payment processing — Phase 2 (routing/blockchain) + Phase 3 (compliance).

Orchestrates: account-suspension check -> sender balance validation ->
asset routing (fees + optional simulated conversion) -> compliance
decisioning (limits/velocity/risk) -> simulated blockchain submission ->
recipient ledger crediting. Every blockchain interaction here goes
through the mock adapter; nothing here touches a real chain.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.blockchain.adapter import get_adapter
from app.models.enums import Asset, ComplianceDecision, Network, PaymentStatus
from app.models.payment import Payment
from app.models.user import User
from app.models.wallet import Wallet
from app.services.audit_service import write_audit_log
from app.services.compliance_service import AccountSuspendedError, assert_account_active, evaluate_transaction
from app.services.ledger_service import credit_ledger_balance
from app.services.routing_service import RoutingError, route_payment


class InsufficientBalanceError(ValueError):
    pass


class PaymentValidationError(ValueError):
    pass


def _get_sender_wallet(db: Session, user_id: str, network: Network) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id, Wallet.network == network).first()
    if wallet is None:
        raise PaymentValidationError("Sender has no wallet on that network")
    return wallet


def create_and_process_payment(
    db: Session,
    sender: User,
    recipient_email: str,
    recipient_id: Optional[str],
    asset: Asset,
    network: Network,
    amount: Decimal,
    settlement_asset: Optional[Asset] = None,
    idempotency_key: Optional[str] = None,
) -> Payment:
    try:
        assert_account_active(sender)
    except AccountSuspendedError as e:
        write_audit_log(
            db,
            action="PAYMENT_BLOCKED_SUSPENDED",
            resource_type="payment",
            actor_user_id=sender.id,
            details=str(e),
        )
        raise PaymentValidationError(str(e)) from e

    wallet = _get_sender_wallet(db, sender.id, network)

    try:
        routing = route_payment(asset, network, amount, settlement_asset)
    except RoutingError as e:
        raise PaymentValidationError(str(e)) from e

    total_debit = amount + routing.network_fee
    if Decimal(wallet.balance) < total_debit:
        raise InsufficientBalanceError(
            f"Insufficient balance: have {wallet.balance}, need {total_debit}"
        )

    compliance = evaluate_transaction(db, sender, amount, asset)

    # Reserve/debit the sender's testnet wallet balance up front, whether
    # the transaction proceeds immediately or is held for review.
    wallet.balance = Decimal(wallet.balance) - total_debit

    payment = Payment(
        sender_id=sender.id,
        recipient_email=recipient_email,
        recipient_id=recipient_id,
        asset=asset,
        network=network,
        amount=amount,
        network_fee=routing.network_fee,
        platform_fee=routing.platform_fee,
        settlement_asset=routing.settlement_asset,
        conversion_rate=routing.conversion_rate,
        conversion_fee=routing.conversion_fee,
        final_amount=routing.final_amount,
        status=PaymentStatus.CREATED,
        idempotency_key=idempotency_key,
        is_flagged=compliance.is_flagged,
        flag_reason="; ".join(compliance.reasons) if compliance.reasons else None,
        held_for_review=(compliance.decision == ComplianceDecision.HELD),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if compliance.decision == ComplianceDecision.HELD:
        payment.status = PaymentStatus.PENDING
        db.commit()
        db.refresh(payment)
        write_audit_log(
            db,
            action="PAYMENT_HELD",
            resource_type="payment",
            resource_id=payment.id,
            actor_user_id=sender.id,
            details=payment.flag_reason,
        )
        return payment

    _submit_payment(db, payment, wallet)
    return payment


def _submit_payment(db: Session, payment: Payment, wallet: Wallet) -> Payment:
    """Submit through a real adapter when configured; otherwise remain explicitly testnet/simulated.

    V2 deliberately never fabricates a blockchain hash or confirmation.
    """
    from app.config import settings
    payment.status = PaymentStatus.PENDING
    payment.environment = "testnet" if settings.blockchain_mode in {"mock", "testnet", "arc_testnet"} else "production"
    payment.settlement_status = "PENDING"
    if settings.blockchain_mode in {"mock", "testnet", "arc_testnet"}:
        # The current project has no real transaction broadcaster for these networks.
        # Funds remain represented in the application's test ledger; no chain claim is made.
        payment.blockchain_tx_hash = None
        db.commit()
        db.refresh(payment)
        write_audit_log(db, action="PAYMENT_TESTNET_PENDING", resource_type="payment",
                        resource_id=payment.id, actor_user_id=payment.sender_id,
                        details="Testnet/simulation: no blockchain transaction was broadcast.")
        return payment
    payment.status = PaymentStatus.FAILED
    payment.failure_reason = "No production blockchain adapter is configured"
    wallet.balance = Decimal(wallet.balance) + payment.amount + payment.network_fee
    db.commit(); db.refresh(payment)
    return payment


def retry_payment(db: Session, payment: Payment) -> Payment:
    if payment.status != PaymentStatus.FAILED:
        raise PaymentValidationError("Only FAILED payments can be retried")

    wallet = _get_sender_wallet(db, payment.sender_id, payment.network)
    total_debit = Decimal(payment.amount) + Decimal(payment.network_fee)
    if Decimal(wallet.balance) < total_debit:
        raise InsufficientBalanceError("Insufficient balance to retry this payment")

    wallet.balance = Decimal(wallet.balance) - total_debit
    payment.failure_reason = None
    db.commit()

    return _submit_payment(db, payment, wallet)


def release_held_payment(db: Session, payment: Payment, reviewer_id: str) -> Payment:
    """Compliance/admin approves a HELD payment; it proceeds to submission."""
    if not payment.held_for_review:
        raise PaymentValidationError("This payment is not held for review")

    wallet = _get_sender_wallet(db, payment.sender_id, payment.network)
    payment.held_for_review = False
    db.commit()
    db.refresh(payment)

    write_audit_log(
        db,
        action="PAYMENT_RELEASED",
        resource_type="payment",
        resource_id=payment.id,
        actor_user_id=reviewer_id,
    )
    return _submit_payment(db, payment, wallet)


def reject_held_payment(db: Session, payment: Payment, reviewer_id: str, reason: str) -> Payment:
    """Compliance/admin rejects a HELD payment; sender is refunded."""
    if not payment.held_for_review:
        raise PaymentValidationError("This payment is not held for review")

    wallet = _get_sender_wallet(db, payment.sender_id, payment.network)
    wallet.balance = Decimal(wallet.balance) + Decimal(payment.amount) + Decimal(payment.network_fee)

    payment.held_for_review = False
    payment.status = PaymentStatus.CANCELLED
    payment.failure_reason = reason
    db.commit()
    db.refresh(payment)

    write_audit_log(
        db,
        action="PAYMENT_REJECTED",
        resource_type="payment",
        resource_id=payment.id,
        actor_user_id=reviewer_id,
        details=reason,
    )
    return payment
