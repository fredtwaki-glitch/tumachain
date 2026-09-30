import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base

def _uuid(): return str(uuid.uuid4())

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(String, primary_key=True, default=_uuid)
    endpoint_id = Column(String, ForeignKey("webhook_endpoints.id"), nullable=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    status = Column(String, nullable=False, default="RECEIVED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    endpoint = relationship("WebhookEndpoint")
