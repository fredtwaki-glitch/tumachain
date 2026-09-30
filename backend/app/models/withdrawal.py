import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import Asset, Network, WithdrawalStatus


def _uuid() -> str:
    return str(uuid.uuid4())


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, unique=True, index=True, default=_uuid, nullable=False)

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    asset = Column(Enum(Asset), nullable=False)
    destination_network = Column(Enum(Network), nullable=False)
    destination_address = Column(String, nullable=False)

    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    network_fee = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.REQUESTED, nullable=False)
    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    blockchain_tx_hash = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)

    # --- Phase 3: compliance ---
    is_flagged = Column(Boolean, default=False, nullable=False)
    flag_reason = Column(String, nullable=True)
    held_for_review = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User")
