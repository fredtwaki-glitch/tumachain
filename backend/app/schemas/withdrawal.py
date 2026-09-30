from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Asset, Network, WithdrawalStatus


class WithdrawalCreate(BaseModel):
    asset: Asset
    destination_network: Network
    destination_address: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    idempotency_key: Optional[str] = None


class WithdrawalOut(BaseModel):
    id: str
    transaction_id: str
    asset: Asset
    destination_network: Network
    destination_address: str
    amount: Decimal
    network_fee: Decimal
    status: WithdrawalStatus
    blockchain_tx_hash: Optional[str]
    failure_reason: Optional[str]
    is_flagged: bool
    flag_reason: Optional[str]
    held_for_review: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
