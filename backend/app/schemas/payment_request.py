from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
class PaymentRequestCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    asset: str = "USDC"
    description: str | None = None
    expires_days: int = Field(default=7, ge=1, le=30)
class PaymentRequestOut(BaseModel):
    id: str; code: str; amount: Decimal; asset: str; description: str | None; expires_at: datetime | None; status: str
    model_config = {"from_attributes": True}
