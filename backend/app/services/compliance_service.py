"""
Compliance decisioning — Phase 3.

Configurable rules (see Settings — NOT hard-coded legal thresholds):

    IF user is not KYC_VERIFIED:
        restrict withdrawals

    IF transaction exceeds configured threshold:
        flag transaction

    IF unusually high transaction velocity occurs:
        flag account

    IF compliance provider returns high risk:
        hold transaction

    IF account is suspended:
        prevent transactions
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from app.compliance.provider import compliance_provider
from app.config import settings
from app.models.enums import Asset, ComplianceDecision, PaymentStatus, VerificationState, WithdrawalStatus
from app.models.payment import Payment
from app.models.user import User
from app.models.withdrawal import Withdrawal
from app.services.exchange_service import exchange_provider


class AccountSuspendedError(ValueError):
    pass


class KycRequiredError(ValueError):
    pass


@dataclass
class ComplianceResult:
    decision: ComplianceDecision
    reasons: List[str]
    risk_score: int

    @property
    def is_flagged(self) -> bool:
        return self.decision != ComplianceDecision.APPROVED


def _daily_limits_usd():
    return {
        VerificationState.UNVERIFIED: Decimal(str(settings.unverified_daily_limit_usd)),
        VerificationState.EMAIL_VERIFIED: Decimal(str(settings.email_verified_daily_limit_usd)),
        VerificationState.KYC_PENDING: Decimal(str(settings.email_verified_daily_limit_usd)),
        VerificationState.KYC_VERIFIED: Decimal(str(settings.kyc_verified_daily_limit_usd)),
        VerificationState.KYC_REJECTED: Decimal(str(settings.unverified_daily_limit_usd)),
        VerificationState.SUSPENDED: Decimal("0"),
    }


def usd_equivalent(amount: Decimal, asset: Asset) -> Decimal:
    rate = exchange_provider.get_rate(asset, Asset.USDC)
    return (amount * rate).quantize(Decimal("0.01"))


def assert_account_active(user: User) -> None:
    if not user.is_active or user.verification_state == VerificationState.SUSPENDED:
        raise AccountSuspendedError("This account is suspended and cannot transact")


def assert_kyc_verified_for_withdrawal(user: User) -> None:
    if user.verification_state != VerificationState.KYC_VERIFIED:
        raise KycRequiredError(
            "Withdrawals require a KYC_VERIFIED account. Submit KYC via POST /kyc/submit."
        )


def _daily_total_usd(db: Session, user_id: str) -> Decimal:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total = Decimal("0")
    payments = (
        db.query(Payment)
        .filter(
            Payment.sender_id == user_id,
            Payment.created_at >= start_of_day,
            Payment.status.notin_([PaymentStatus.FAILED, PaymentStatus.CANCELLED]),
        )
        .all()
    )
    for p in payments:
        total += usd_equivalent(Decimal(p.amount), p.asset)

    withdrawals = (
        db.query(Withdrawal)
        .filter(
            Withdrawal.user_id == user_id,
            Withdrawal.created_at >= start_of_day,
            Withdrawal.status.notin_([WithdrawalStatus.FAILED, WithdrawalStatus.REJECTED]),
        )
        .all()
    )
    for w in withdrawals:
        total += usd_equivalent(Decimal(w.amount), w.asset)

    return total


def _tx_count_last_hour(db: Session, user_id: str) -> int:
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    payment_count = (
        db.query(Payment)
        .filter(Payment.sender_id == user_id, Payment.created_at >= one_hour_ago)
        .count()
    )
    withdrawal_count = (
        db.query(Withdrawal)
        .filter(Withdrawal.user_id == user_id, Withdrawal.created_at >= one_hour_ago)
        .count()
    )
    return payment_count + withdrawal_count


def evaluate_transaction(
    db: Session, user: User, amount: Decimal, asset: Asset
) -> ComplianceResult:
    reasons: List[str] = []
    decision = ComplianceDecision.APPROVED

    amount_usd = usd_equivalent(amount, asset)

    daily_limit = _daily_limits_usd().get(user.verification_state, Decimal("0"))
    daily_total = _daily_total_usd(db, user.id) + amount_usd
    if daily_total > daily_limit:
        decision = ComplianceDecision.HELD
        reasons.append(
            f"Daily transaction limit exceeded (${daily_total} > ${daily_limit} for "
            f"{user.verification_state.value})"
        )

    tx_count = _tx_count_last_hour(db, user.id) + 1
    if tx_count > settings.velocity_max_tx_per_hour:
        decision = ComplianceDecision.HELD
        reasons.append(
            f"High transaction velocity ({tx_count} transactions in the last hour)"
        )

    risk = compliance_provider.assess_risk(amount_usd, user.country or "")
    if risk.is_high_risk:
        decision = ComplianceDecision.HELD
        reasons.append(f"High risk score from compliance provider ({risk.risk_score})")

    if amount_usd >= Decimal(str(settings.large_transaction_flag_usd)):
        decision = ComplianceDecision.HELD
        reasons.append(
            f"Large transaction (${amount_usd} >= ${settings.large_transaction_flag_usd})"
        )

    return ComplianceResult(decision=decision, reasons=reasons, risk_score=risk.risk_score)
