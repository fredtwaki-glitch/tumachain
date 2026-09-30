import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

def _uuid(): return str(uuid.uuid4())
class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    id = Column(String, primary_key=True, default=_uuid)
    code = Column(String, unique=True, index=True, nullable=False)
    creator_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(36,18), nullable=False)
    asset = Column(String, nullable=False, default="USDC")
    description = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="OPEN")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    creator = relationship("User")
