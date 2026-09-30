import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    """
    Append-only-by-convention audit trail. Nothing in the app updates or
    deletes rows here — entries are written once, at the moment an
    action happens, and never edited afterward.
    """

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True)  # null = system action
    action = Column(String, nullable=False)  # e.g. "PAYMENT_HELD", "KYC_APPROVED"
    resource_type = Column(String, nullable=False)  # e.g. "payment", "withdrawal", "user"
    resource_id = Column(String, nullable=True)
    details = Column(String, nullable=True)  # short human-readable note, not structured data

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    actor = relationship("User", foreign_keys=[actor_user_id])
