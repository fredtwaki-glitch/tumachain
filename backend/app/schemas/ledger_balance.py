from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Asset, Network


class LedgerBalanceOut(BaseModel):
    asset: Asset
    amount: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FaucetRequest(BaseModel):
    network: Network
    amount: Decimal = Field(gt=0)
