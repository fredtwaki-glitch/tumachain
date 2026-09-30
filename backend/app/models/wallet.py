import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import Network


def _uuid() -> str:
    return str(uuid.uuid4())


class Wallet(Base):
    """
    One row per (user, network). Holds a mock/testnet address and an
    internal ledger balance. Private keys are represented only as an
    internal, never-serialized field — Phase 1 uses deterministic mock
    keys and NEVER exposes them via the API.
    """

    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("user_id", "network", name="uq_user_network"),)

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    network = Column(Enum(Network), nullable=False)
    address = Column(String, nullable=False, index=True)

    # Never returned by any schema/response model.
    _mock_private_key = Column("mock_private_key", String, nullable=False)

    balance = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="wallets")
