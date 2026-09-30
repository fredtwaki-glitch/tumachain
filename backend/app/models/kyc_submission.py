import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import KycStatus


def _uuid() -> str:
    return str(uuid.uuid4())


class KycSubmission(Base):
    __tablename__ = "kyc_submissions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    full_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    document_type = Column(String, nullable=False)  # e.g. "passport", "national_id"
    document_reference = Column(String, nullable=False)  # never a real document image/number

    status = Column(Enum(KycStatus), default=KycStatus.PENDING, nullable=False)
    rejection_reason = Column(String, nullable=True)

    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", foreign_keys=[user_id])
