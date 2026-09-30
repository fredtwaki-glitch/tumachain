from dataclasses import dataclass
from decimal import Decimal
from app.config import settings

@dataclass
class SettlementQuote:
    amount: Decimal
    asset: str
    destination_method: str
    destination_currency: str | None
    fee: Decimal
    total: Decimal
    provider: str
    environment: str

class SettlementProvider:
    name="abstract"
    environment="testnet"
    def create_quote(self, amount, asset, destination_method, destination_currency=None): raise NotImplementedError
    def execute_settlement(self, *args, **kwargs): raise NotImplementedError
    def get_status(self, *args, **kwargs): raise NotImplementedError
    def get_supported_methods(self): return []

class TestnetSettlementProvider(SettlementProvider):
    name="testnet_mock"
    environment="testnet"
    def create_quote(self, amount, asset, destination_method, destination_currency=None):
        fee=(amount*Decimal("0.005")).quantize(Decimal("0.00000001")) if destination_method!="wallet" else Decimal("0")
        return SettlementQuote(amount,asset,destination_method,destination_currency,fee,amount+fee,self.name,self.environment)
    def execute_settlement(self, *args, **kwargs):
        return {"status":"PENDING","environment":"testnet","executed":False,"message":"No real-world settlement executed."}
    def get_status(self, *args, **kwargs):
        return {"status":"PENDING","environment":"testnet"}
    def get_supported_methods(self): return ["wallet","stablecoin","local_currency"]

settlement_provider=TestnetSettlementProvider()
