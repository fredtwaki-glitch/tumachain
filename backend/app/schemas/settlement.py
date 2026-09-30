from decimal import Decimal
from pydantic import BaseModel, Field
class SettlementQuoteRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    asset: str = "USDC"
    destination_method: str = "wallet"
    destination_currency: str | None = None
class SettlementQuoteOut(BaseModel):
    amount: Decimal; asset: str; destination_method: str; destination_currency: str | None; fee: Decimal; total: Decimal; provider: str; environment: str
