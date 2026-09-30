from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.enums import KycStatus
from app.models.kyc_submission import KycSubmission
from app.models.payment import Payment
from app.models.user import User
from app.models.wallet import Wallet
from app.models.withdrawal import Withdrawal
from app.models.payment_request import PaymentRequest
from app.models.settlement import Settlement
from app.models.merchant import ApiCredential, WebhookEndpoint
from app.models.webhook import WebhookEvent
from app.schemas.audit_log import AuditLogOut
from app.schemas.kyc import KycOut
from app.schemas.payment import PaymentOut
from app.schemas.user import UserOut
from app.schemas.wallet import WalletOut
from app.schemas.withdrawal import WithdrawalOut
from app.security.rbac import require_admin, require_compliance
from app.services.account_service import AccountServiceError, suspend_user, unsuspend_user
from app.services.kyc_service import KycValidationError, approve_kyc, reject_kyc
from app.services.payment_processing import (
    PaymentValidationError as PaymentReviewError,
    reject_held_payment,
    release_held_payment,
)
from app.services.withdrawal_processing import (
    WithdrawalValidationError as WithdrawalReviewError,
    reject_held_withdrawal,
    release_held_withdrawal,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class SuspendRequest(BaseModel):
    reason: str


class RejectRequest(BaseModel):
    reason: str


@router.get("/summary")
def admin_summary(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {
        "users": db.query(User).count(),
        "wallets": db.query(Wallet).count(),
        "payments": db.query(Payment).count(),
        "withdrawals": db.query(Withdrawal).count(),
        "kyc_pending": db.query(KycSubmission).filter(KycSubmission.status == KycStatus.PENDING).count(),
        "held_payments": db.query(Payment).filter(Payment.held_for_review.is_(True)).count(),
        "held_withdrawals": db.query(Withdrawal).filter(Withdrawal.held_for_review.is_(True)).count(),
        "payment_links": db.query(PaymentRequest).count(),
        "settlements": db.query(Settlement).count(),
        "api_keys": db.query(ApiCredential).count(),
        "webhooks": db.query(WebhookEndpoint).count(),
        "webhook_events": db.query(WebhookEvent).count(),
        "mode": "TESTNET/SIMULATED",
    }


@router.get("/users", response_model=List[UserOut])
def admin_list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).all()


@router.get("/payments", response_model=List[PaymentOut])
def admin_list_payments(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(Payment).all()


@router.get("/wallets", response_model=List[WalletOut])
def admin_list_wallets(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(Wallet).all()


@router.get("/withdrawals", response_model=List[WithdrawalOut])
def admin_list_withdrawals(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(Withdrawal).all()


@router.get("/payment-links")
def admin_payment_links(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(PaymentRequest).order_by(PaymentRequest.created_at.desc()).all()

@router.get("/settlements")
def admin_settlements(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(Settlement).order_by(Settlement.created_at.desc()).all()

@router.get("/api-keys")
def admin_api_keys(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return [{"id":r.id,"user_id":r.user_id,"name":r.name,"key_prefix":r.key_prefix,"active":r.active,"created_at":r.created_at} for r in db.query(ApiCredential).all()]

@router.get("/webhooks")
def admin_webhooks(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return [{"id":r.id,"user_id":r.user_id,"url":r.url,"active":r.active,"created_at":r.created_at} for r in db.query(WebhookEndpoint).all()]

@router.get("/system-health")
def admin_system_health(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {"status":"ok","database":"ok","environment":"testnet","fake_live_settlement":False,"fake_blockchain_confirmation":False}

# --- Flagged / held transactions -------------------------------------------------


@router.get("/flagged/payments", response_model=List[PaymentOut])
def admin_flagged_payments(db: Session = Depends(get_db), _c: User = Depends(require_compliance)):
    return db.query(Payment).filter(Payment.is_flagged.is_(True)).all()


@router.get("/flagged/withdrawals", response_model=List[WithdrawalOut])
def admin_flagged_withdrawals(db: Session = Depends(get_db), _c: User = Depends(require_compliance)):
    return db.query(Withdrawal).filter(Withdrawal.is_flagged.is_(True)).all()


@router.post("/payments/{payment_id}/release", response_model=PaymentOut)
def admin_release_payment(
    payment_id: str, db: Session = Depends(get_db), reviewer: User = Depends(require_compliance)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    try:
        return release_held_payment(db, payment, reviewer.id)
    except PaymentReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/payments/{payment_id}/reject", response_model=PaymentOut)
def admin_reject_payment(
    payment_id: str,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_compliance),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    try:
        return reject_held_payment(db, payment, reviewer.id, payload.reason)
    except PaymentReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/withdrawals/{withdrawal_id}/release", response_model=WithdrawalOut)
def admin_release_withdrawal(
    withdrawal_id: str, db: Session = Depends(get_db), reviewer: User = Depends(require_compliance)
):
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")
    try:
        return release_held_withdrawal(db, withdrawal, reviewer.id)
    except WithdrawalReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/withdrawals/{withdrawal_id}/reject", response_model=WithdrawalOut)
def admin_reject_withdrawal(
    withdrawal_id: str,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_compliance),
):
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")
    try:
        return reject_held_withdrawal(db, withdrawal, reviewer.id, payload.reason)
    except WithdrawalReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- KYC review --------------------------------------------------------------------


@router.get("/kyc/pending", response_model=List[KycOut])
def admin_list_pending_kyc(db: Session = Depends(get_db), _c: User = Depends(require_compliance)):
    return db.query(KycSubmission).filter(KycSubmission.status == KycStatus.PENDING).all()


@router.post("/kyc/{submission_id}/approve", response_model=KycOut)
def admin_approve_kyc(
    submission_id: str, db: Session = Depends(get_db), reviewer: User = Depends(require_compliance)
):
    submission = db.query(KycSubmission).filter(KycSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    try:
        return approve_kyc(db, submission, reviewer.id)
    except KycValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/kyc/{submission_id}/reject", response_model=KycOut)
def admin_reject_kyc(
    submission_id: str,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_compliance),
):
    submission = db.query(KycSubmission).filter(KycSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    try:
        return reject_kyc(db, submission, reviewer.id, payload.reason)
    except KycValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Account suspension --------------------------------------------------------------


@router.post("/users/{user_id}/suspend", response_model=UserOut)
def admin_suspend_user(
    user_id: str,
    payload: SuspendRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        return suspend_user(db, user, admin.id, payload.reason)
    except AccountServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/unsuspend", response_model=UserOut)
def admin_unsuspend_user(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        return unsuspend_user(db, user, admin.id)
    except AccountServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Audit logs ----------------------------------------------------------------------


@router.get("/audit-logs", response_model=List[AuditLogOut])
def admin_list_audit_logs(
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = db.query(AuditLog)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    return query.order_by(AuditLog.created_at.desc()).all()
