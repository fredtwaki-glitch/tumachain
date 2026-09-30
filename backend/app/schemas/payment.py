from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Asset, Network, PaymentStatus


class PaymentCreate(BaseModel):
    recipient_email: Optional[EmailStr] = None
    recipient_identifier: Optional[str] = None
    asset: Asset
    network: Network
    amount: Decimal = Field(gt=0)
    settlement_asset: Optional[Asset] = None  # None => same as `asset` (no conversion)
    idempotency_key: Optional[str] = None


class PaymentOut(BaseModel):
    id: str
    transaction_id: str
    recipient_email: Optional[EmailStr] = None
    recipient_identifier: Optional[str] = None
    asset: Asset
    network: Network
    amount: Decimal
    network_fee: Decimal
    platform_fee: Decimal
    settlement_asset: Optional[Asset]
    conversion_rate: Optional[Decimal]
    conversion_fee: Decimal
    final_amount: Optional[Decimal]
    status: PaymentStatus
    blockchain_tx_hash: Optional[str]
    failure_reason: Optional[str]
    is_flagged: bool
    flag_reason: Optional[str]
    held_for_review: bool
    settlement_status: str = "PENDING"
    environment: str = "testnet"
    fee: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
