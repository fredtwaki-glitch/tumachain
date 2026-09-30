import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import Asset, Network, PaymentStatus


def _uuid() -> str:
    return str(uuid.uuid4())


class Payment(Base):
    """
    The internal ledger record for a single Pay-via-Mail payment.
    A row here does NOT mean funds have moved — see `status`.
    """

    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, unique=True, index=True, default=_uuid, nullable=False)

    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    recipient_email = Column(String, index=True, nullable=True)
    recipient_identifier = Column(String, index=True, nullable=True)
    destination_chain = Column(Enum(Network), nullable=True)
    # Populated once/if the recipient has an account with this email.
    recipient_id = Column(String, ForeignKey("users.id"), nullable=True)

    asset = Column(Enum(Asset), nullable=False)
    network = Column(Enum(Network), nullable=False)
    amount = Column(Numeric(precision=36, scale=18), nullable=False)

    network_fee = Column(Numeric(precision=36, scale=18), default=0, nullable=False)
    platform_fee = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    # --- Phase 2: cross-chain routing / conversion ---
    settlement_asset = Column(Enum(Asset), nullable=True)  # defaults to `asset` if not converting
    conversion_rate = Column(Numeric(precision=36, scale=18), nullable=True)
    conversion_fee = Column(Numeric(precision=36, scale=18), default=0, nullable=False)
    final_amount = Column(Numeric(precision=36, scale=18), nullable=True)  # amount credited to recipient's ledger
    blockchain_tx_hash = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)

    # --- Phase 3: compliance ---
    is_flagged = Column(Boolean, default=False, nullable=False)
    flag_reason = Column(String, nullable=True)
    held_for_review = Column(Boolean, default=False, nullable=False)

    status = Column(Enum(PaymentStatus), default=PaymentStatus.CREATED, nullable=False)
    is_confirmed = Column(String, default="false", nullable=False)  # simple flag for Phase 1

    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    settlement_status = Column(String, nullable=False, default="PENDING")
    environment = Column(String, nullable=False, default="testnet")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sender = relationship("User", back_populates="sent_payments", foreign_keys=[sender_id])
