from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.compliance.provider import compliance_provider
from app.models.enums import KycStatus, VerificationState
from app.models.kyc_submission import KycSubmission
from app.models.user import User
from app.services.audit_service import write_audit_log


class KycValidationError(ValueError):
    pass


def submit_kyc(
    db: Session,
    user: User,
    full_name: str,
    country: str,
    document_type: str,
    document_reference: str,
) -> KycSubmission:
    existing_pending = (
        db.query(KycSubmission)
        .filter(KycSubmission.user_id == user.id, KycSubmission.status == KycStatus.PENDING)
        .first()
    )
    if existing_pending:
        raise KycValidationError("A KYC submission is already pending review")

    submission = KycSubmission(
        user_id=user.id,
        full_name=full_name,
        country=country,
        document_type=document_type,
        document_reference=document_reference,
        status=KycStatus.PENDING,
    )
    db.add(submission)

    user.country = country
    if user.verification_state in (VerificationState.UNVERIFIED, VerificationState.EMAIL_VERIFIED, VerificationState.KYC_REJECTED):
        user.verification_state = VerificationState.KYC_PENDING

    db.commit()
    db.refresh(submission)

    write_audit_log(
        db,
        action="KYC_SUBMITTED",
        resource_type="kyc_submission",
        resource_id=submission.id,
        actor_user_id=user.id,
    )
    return submission


def approve_kyc(db: Session, submission: KycSubmission, reviewer_id: str) -> KycSubmission:
    if submission.status != KycStatus.PENDING:
        raise KycValidationError("Only PENDING submissions can be reviewed")

    # Safety-net automated sanctions screen — even a manual approval can't
    # clear a submission that the compliance provider flags as sanctioned.
    sanctions_clear = compliance_provider.screen_sanctions(submission.full_name, submission.country)
    if not sanctions_clear:
        return reject_kyc(db, submission, reviewer_id, "Sanctions screening hit")

    submission.status = KycStatus.APPROVED
    submission.reviewed_by = reviewer_id
    submission.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)

    user = db.query(User).filter(User.id == submission.user_id).first()
    if user:
        user.verification_state = VerificationState.KYC_VERIFIED
        db.commit()

    write_audit_log(
        db,
        action="KYC_APPROVED",
        resource_type="kyc_submission",
        resource_id=submission.id,
        actor_user_id=reviewer_id,
    )
    return submission


def reject_kyc(db: Session, submission: KycSubmission, reviewer_id: str, reason: str) -> KycSubmission:
    if submission.status != KycStatus.PENDING:
        raise KycValidationError("Only PENDING submissions can be reviewed")

    submission.status = KycStatus.REJECTED
    submission.rejection_reason = reason
    submission.reviewed_by = reviewer_id
    submission.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)

    user = db.query(User).filter(User.id == submission.user_id).first()
    if user:
        user.verification_state = VerificationState.KYC_REJECTED
        db.commit()

    write_audit_log(
        db,
        action="KYC_REJECTED",
        resource_type="kyc_submission",
        resource_id=submission.id,
        actor_user_id=reviewer_id,
        details=reason,
    )
    return submission
