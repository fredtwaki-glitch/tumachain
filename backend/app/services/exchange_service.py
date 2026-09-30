"""
Mock exchange / liquidity provider.

All conversions here are TESTNET / SIMULATED using fixed, made-up
rates — never a real market feed. A real implementation (a DEX
aggregator, a CEX API, or a liquidity provider) would implement the
same `ExchangeProvider` interface later.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Tuple

from app.models.enums import Asset

CONVERSION_FEE_RATE = Decimal("0.005")  # 0.5%, simulated


class ExchangeProvider(ABC):
    @abstractmethod
    def get_rate(self, from_asset: Asset, to_asset: Asset) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def convert(
        self, amount: Decimal, from_asset: Asset, to_asset: Asset
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Returns (converted_amount_before_fee, rate, conversion_fee_in_to_asset)."""
        raise NotImplementedError


class MockExchangeProvider(ExchangeProvider):
    # Fixed, clearly-fake mock rates, quoted as "1 unit of asset = X USDC".
    _USD_RATES = {
        Asset.BTC: Decimal("60000"),
        Asset.ETH: Decimal("3000"),
        Asset.SOL: Decimal("150"),
        Asset.EVMT: Decimal("1"),
        Asset.USDC: Decimal("1"),
    }

    def get_rate(self, from_asset: Asset, to_asset: Asset) -> Decimal:
        if from_asset == to_asset:
            return Decimal("1")
        from_usd = self._USD_RATES[from_asset]
        to_usd = self._USD_RATES[to_asset]
        return (from_usd / to_usd).quantize(Decimal("0.00000001"))

    def convert(
        self, amount: Decimal, from_asset: Asset, to_asset: Asset
    ) -> Tuple[Decimal, Decimal, Decimal]:
        rate = self.get_rate(from_asset, to_asset)
        gross_converted = (amount * rate).quantize(Decimal("0.00000001"))
        if from_asset == to_asset:
            return gross_converted, rate, Decimal("0")
        conversion_fee = (gross_converted * CONVERSION_FEE_RATE).quantize(Decimal("0.00000001"))
        return gross_converted, rate, conversion_fee


exchange_provider = MockExchangeProvider()
