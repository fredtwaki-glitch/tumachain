import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from app.database import Base

def _uuid(): return str(uuid.uuid4())
class Settlement(Base):
    __tablename__ = "settlements"
    id = Column(String, primary_key=True, default=_uuid)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, default="testnet_mock")
    source_asset = Column(String, nullable=False)
    destination_method = Column(String, nullable=False)
    destination_currency = Column(String, nullable=True)
    amount = Column(Numeric(36,18), nullable=False)
    fee = Column(Numeric(36,18), nullable=False, default=0)
    status = Column(String, nullable=False, default="CREATED")
    environment = Column(String, nullable=False, default="testnet")
    provider_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    payment = relationship("Payment")
    user = relationship("User")
