from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import Network


class WalletOut(BaseModel):
    id: str
    network: Network
    address: str
    balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
