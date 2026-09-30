from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import KycStatus


class KycSubmit(BaseModel):
    full_name: str = Field(min_length=1)
    country: str = Field(min_length=1)
    document_type: str = Field(min_length=1)  # e.g. "passport", "national_id"
    document_reference: str = Field(min_length=1)  # never a real doc image/number in this app


class KycOut(BaseModel):
    id: str
    full_name: str
    country: str
    document_type: str
    status: KycStatus
    rejection_reason: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class KycReviewRequest(BaseModel):
    rejection_reason: Optional[str] = None  # required (by the endpoint) only when rejecting
