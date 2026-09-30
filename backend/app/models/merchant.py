import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

def _uuid(): return str(uuid.uuid4())
class ApiCredential(Base):
    __tablename__ = "api_credentials"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    key_prefix = Column(String, nullable=False, index=True)
    key_hash = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User")

class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    secret_hash = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User")
