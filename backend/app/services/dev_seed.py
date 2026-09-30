"""Development-only database bootstrap helpers.

This module creates the default local administrator requested for the
TumaChain sandbox. It is deliberately gated behind APP_ENV=development and
DEV_AUTO_CREATE_ADMIN=true so the convenience credential cannot be enabled
accidentally in production.
"""

from sqlalchemy.orm import Session

from app.config import settings
from app.models.enums import UserRole, VerificationState
from app.models.user import User
from app.security.passwords import hash_password
from app.services.wallet_service import create_wallets_for_user


def ensure_development_admin(db: Session) -> User | None:
    """Create/update the local development admin and return it.

    The credentials are configurable through DEV_ADMIN_EMAIL and
    DEV_ADMIN_PASSWORD. On every development startup, the reserved admin
    account is kept usable with those credentials, marked email-verified, and
    assigned ADMIN role. No real-money or production functionality is enabled.
    """
    if settings.app_env.lower() != "development" or not settings.dev_auto_create_admin:
        return None

    email = settings.dev_admin_email.strip().lower()
    if not email or not settings.dev_admin_password:
        raise RuntimeError("Development admin credentials are not configured")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(settings.dev_admin_password),
            full_name=settings.dev_admin_full_name,
            role=UserRole.ADMIN,
            verification_state=VerificationState.EMAIL_VERIFIED,
            email_verification_token=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        create_wallets_for_user(db, user)
        return user

    # This email is reserved for the local development administrator.
    # Keep the account immediately usable after a database reset/restart.
    changed = False
    if user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN
        changed = True
    if user.verification_state != VerificationState.EMAIL_VERIFIED:
        user.verification_state = VerificationState.EMAIL_VERIFIED
        changed = True
    if user.email_verification_token is not None:
        user.email_verification_token = None
        changed = True
    if user.hashed_password and not _password_matches(settings.dev_admin_password, user.hashed_password):
        user.hashed_password = hash_password(settings.dev_admin_password)
        changed = True

    if changed:
        db.commit()
        db.refresh(user)

    # A partially initialized development DB may contain the user but no
    # wallets, so make sure the standard wallet records exist.
    if not user.wallets:
        create_wallets_for_user(db, user)

    return user


def _password_matches(password: str, hashed_password: str) -> bool:
    from app.security.passwords import verify_password

    try:
        return verify_password(password, hashed_password)
    except Exception:
        return False
