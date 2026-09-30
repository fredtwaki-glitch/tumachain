import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import Asset


def _uuid() -> str:
    return str(uuid.uuid4())


class LedgerBalance(Base):
    """
    A user's available, off-chain internal balance per asset — the
    "AVAILABLE_BALANCE" step in the payment lifecycle. This is what
    payments settle into (after optional conversion) and what
    withdrawals draw down from. It is intentionally separate from the
    per-network testnet `Wallet.balance`, which represents funds still
    on a specific mock chain.
    """

    __tablename__ = "ledger_balances"
    __table_args__ = (UniqueConstraint("user_id", "asset", name="uq_user_asset_ledger"),)

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    asset = Column(Enum(Asset), nullable=False)
    amount = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User")
