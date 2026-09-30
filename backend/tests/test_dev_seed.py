from app.config import settings
from app.models.enums import UserRole, VerificationState
from app.models.user import User
from app.security.passwords import verify_password
from app.services.dev_seed import ensure_development_admin


def test_development_admin_bootstrap(db_session):
    old_env = settings.app_env
    old_enabled = settings.dev_auto_create_admin
    old_email = settings.dev_admin_email
    old_password = settings.dev_admin_password
    try:
        settings.app_env = "development"
        settings.dev_auto_create_admin = True
        settings.dev_admin_email = "admin@example.com"
        settings.dev_admin_password = "walenisi1"

        admin = ensure_development_admin(db_session)
        assert admin is not None
        assert admin.email == "admin@example.com"
        assert admin.role == UserRole.ADMIN
        assert admin.verification_state == VerificationState.EMAIL_VERIFIED
        assert verify_password("walenisi1", admin.hashed_password)

        # Idempotent: a second initialization must not create a duplicate.
        ensure_development_admin(db_session)
        assert db_session.query(User).filter(User.email == "admin@example.com").count() == 1
    finally:
        settings.app_env = old_env
        settings.dev_auto_create_admin = old_enabled
        settings.dev_admin_email = old_email
        settings.dev_admin_password = old_password
