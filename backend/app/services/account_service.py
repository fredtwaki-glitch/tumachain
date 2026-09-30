from sqlalchemy.orm import Session

from app.models.enums import VerificationState
from app.models.user import User
from app.services.audit_service import write_audit_log


class AccountServiceError(ValueError):
    pass


def suspend_user(db: Session, user: User, admin_id: str, reason: str) -> User:
    if user.verification_state == VerificationState.SUSPENDED:
        raise AccountServiceError("User is already suspended")

    # Deliberately does NOT set is_active=False: that flag gates login
    # itself (see security/dependencies.py), and a suspended user should
    # still be able to log in to see their account status — they just
    # can't transact. Transaction-blocking is enforced via
    # compliance_service.assert_account_active, which checks
    # verification_state == SUSPENDED.
    user.suspended_previous_state = user.verification_state.value
    user.verification_state = VerificationState.SUSPENDED
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        action="USER_SUSPENDED",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=admin_id,
        details=reason,
    )
    return user


def unsuspend_user(db: Session, user: User, admin_id: str) -> User:
    if user.verification_state != VerificationState.SUSPENDED:
        raise AccountServiceError("User is not suspended")

    restored_state = (
        VerificationState(user.suspended_previous_state)
        if user.suspended_previous_state
        else VerificationState.EMAIL_VERIFIED
    )
    user.verification_state = restored_state
    user.suspended_previous_state = None
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        action="USER_UNSUSPENDED",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=admin_id,
    )
    return user
