from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    id: str
    actor_user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
