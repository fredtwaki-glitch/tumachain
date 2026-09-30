"""
Dev-only helper: promote a user to ADMIN by email.

Usage (from backend/):
    python ../scripts/make_admin.py user@example.com

Never expose an "become admin" API endpoint — role changes like this
should go through a trusted internal path (this script, or later, a
proper super-admin-only endpoint with audit logging).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402


def make_admin(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"No user found with email: {email}")
            return
        user.role = UserRole.ADMIN
        db.commit()
        print(f"{email} is now ADMIN.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)
    make_admin(sys.argv[1])
