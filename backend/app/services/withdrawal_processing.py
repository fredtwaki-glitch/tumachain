"""
Withdrawal processing — Phase 2 (blockchain) + Phase 3 (compliance).

Validates destination + balance, enforces the KYC-verified requirement
for ALL withdrawals, runs compliance decisioning (limits/velocity/risk),
debits the user's internal ledger, then simulates blockchain submission
via the mock adapter. No real withdrawal is ever performed.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.blockchain.adapter import get_adapter
from app.models.enums import Asset, ComplianceDecision, Network, WithdrawalStatus
from app.models.withdrawal import Withdrawal
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.compliance_service import (
    AccountSuspendedError,
    KycRequiredError,
    assert_account_active,
    assert_kyc_verified_for_withdrawal,
    evaluate_transaction,
)
from app.services.ledger_service import credit_ledger_balance, debit_ledger_balance, get_or_create_ledger_balance

MIN_WITHDRAWAL_AMOUNT = Decimal("0.0001")


class WithdrawalValidationError(ValueError):
    pass


class InsufficientLedgerBalanceError(ValueError):
    pass


def request_withdrawal(
    db: Session,
    user: User,
    asset: Asset,
    destination_network: Network,
    destination_address: str,
    amount: Decimal,
    idempotency_key: Optional[str] = None,
) -> Withdrawal:
    if idempotency_key:
        existing = (
            db.query(Withdrawal).filter(Withdrawal.idempotency_key == idempotency_key).first()
        )
        if existing:
            return existing

    try:
        assert_account_active(user)
    except AccountSuspendedError as e:
        write_audit_log(
            db,
            action="WITHDRAWAL_BLOCKED_SUSPENDED",
            resource_type="withdrawal",
            actor_user_id=user.id,
            details=str(e),
        )
        raise WithdrawalValidationError(str(e)) from e

    try:
        assert_kyc_verified_for_withdrawal(user)
    except KycRequiredError as e:
        write_audit_log(
            db,
            action="WITHDRAWAL_BLOCKED_KYC_REQUIRED",
            resource_type="withdrawal",
            actor_user_id=user.id,
            details=str(e),
        )
        raise WithdrawalValidationError(str(e)) from e

    if amount < MIN_WITHDRAWAL_AMOUNT:
        raise WithdrawalValidationError(
            f"Amount is below the minimum withdrawal of {MIN_WITHDRAWAL_AMOUNT}"
        )

    adapter = get_adapter(destination_network)
    if not adapter.validate_address(destination_address):
        raise WithdrawalValidationError("Invalid destination address for that network")

    network_fee = adapter.estimate_fee(amount)
    total_debit = amount + network_fee

    ledger = get_or_create_ledger_balance(db, user.id, asset)
    if Decimal(ledger.amount) < total_debit:
        raise InsufficientLedgerBalanceError(
            f"Insufficient balance: have {ledger.amount}, need {total_debit}"
        )

    compliance = evaluate_transaction(db, user, amount, asset)

    debit_ledger_balance(db, user.id, asset, total_debit)

    withdrawal = Withdrawal(
        user_id=user.id,
        asset=asset,
        destination_network=destination_network,
        destination_address=destination_address,
        amount=amount,
        network_fee=network_fee,
        status=WithdrawalStatus.REQUESTED,
        idempotency_key=idempotency_key,
        is_flagged=compliance.is_flagged,
        flag_reason="; ".join(compliance.reasons) if compliance.reasons else None,
        held_for_review=(compliance.decision == ComplianceDecision.HELD),
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)

    if compliance.decision == ComplianceDecision.HELD:
        write_audit_log(
            db,
            action="WITHDRAWAL_HELD",
            resource_type="withdrawal",
            resource_id=withdrawal.id,
            actor_user_id=user.id,
            details=withdrawal.flag_reason,
        )
        return withdrawal

    return _process_withdrawal(db, withdrawal)


def _process_withdrawal(db: Session, withdrawal: Withdrawal) -> Withdrawal:
    from app.config import settings
    withdrawal.status = WithdrawalStatus.PROCESSING
    db.commit()
    if settings.blockchain_mode in {"mock", "testnet", "arc_testnet"}:
        withdrawal.status = WithdrawalStatus.PROCESSING
        withdrawal.blockchain_tx_hash = None
        db.commit(); db.refresh(withdrawal)
        write_audit_log(db, action="WITHDRAWAL_TESTNET_PENDING", resource_type="withdrawal",
                        resource_id=withdrawal.id, actor_user_id=withdrawal.user_id,
                        details="Testnet/simulation: no blockchain transaction was broadcast.")
        return withdrawal
    withdrawal.status = WithdrawalStatus.FAILED
    withdrawal.failure_reason = "No production blockchain adapter is configured"
    credit_ledger_balance(db, withdrawal.user_id, withdrawal.asset, withdrawal.amount + withdrawal.network_fee)
    db.commit(); db.refresh(withdrawal)
    return withdrawal


def release_held_withdrawal(db: Session, withdrawal: Withdrawal, reviewer_id: str) -> Withdrawal:
    if not withdrawal.held_for_review:
        raise WithdrawalValidationError("This withdrawal is not held for review")

    withdrawal.held_for_review = False
    db.commit()
    db.refresh(withdrawal)

    write_audit_log(
        db,
        action="WITHDRAWAL_RELEASED",
        resource_type="withdrawal",
        resource_id=withdrawal.id,
        actor_user_id=reviewer_id,
    )
    return _process_withdrawal(db, withdrawal)


def reject_held_withdrawal(db: Session, withdrawal: Withdrawal, reviewer_id: str, reason: str) -> Withdrawal:
    if not withdrawal.held_for_review:
        raise WithdrawalValidationError("This withdrawal is not held for review")

    credit_ledger_balance(
        db, withdrawal.user_id, withdrawal.asset, withdrawal.amount + withdrawal.network_fee
    )
    withdrawal.held_for_review = False
    withdrawal.status = WithdrawalStatus.REJECTED
    withdrawal.failure_reason = reason
    db.commit()
    db.refresh(withdrawal)

    write_audit_log(
        db,
        action="WITHDRAWAL_REJECTED",
        resource_type="withdrawal",
        resource_id=withdrawal.id,
        actor_user_id=reviewer_id,
        details=reason,
    )
    return withdrawal
