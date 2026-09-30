import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import UserRole, VerificationState


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    profile_photo_url = Column(String, nullable=True)
    preferred_settlement_method = Column(String, nullable=True, default="stablecoin")
    notification_preferences = Column(String, nullable=True, default="{}")
    kyc_status = Column(String, nullable=False, default="UNVERIFIED")
    kyb_status = Column(String, nullable=False, default="NOT_APPLICABLE")
    aml_status = Column(String, nullable=False, default="CLEAR")
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    country = Column(String, nullable=True)  # ISO-ish free text; used for jurisdiction/compliance

    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    verification_state = Column(
        Enum(VerificationState), default=VerificationState.UNVERIFIED, nullable=False
    )

    is_active = Column(Boolean, default=True, nullable=False)
    suspended_previous_state = Column(String, nullable=True)  # restored on unsuspend

    email_verification_token = Column(String, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    wallets = relationship("Wallet", back_populates="owner", cascade="all, delete-orphan")
    sent_payments = relationship(
        "Payment", back_populates="sender", foreign_keys="Payment.sender_id"
    )
