"""
Internal asset-routing engine.

Given a sender's chosen asset/network/amount and an optional requested
settlement asset, this determines: the network fee, the platform fee,
whether a (simulated) conversion is needed, the conversion rate/fee,
and the final amount the recipient's internal ledger will be credited.

Everything here is TESTNET / SIMULATED.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.blockchain.adapter import get_adapter
from app.models.enums import Asset, Network
from app.services.exchange_service import exchange_provider

PLATFORM_FEE_RATE = Decimal("0.001")  # 0.1%, simulated


class RoutingError(ValueError):
    pass


@dataclass
class RoutingResult:
    source_asset: Asset
    source_network: Network
    settlement_asset: Asset
    network_fee: Decimal
    conversion_rate: Decimal
    conversion_fee: Decimal
    platform_fee: Decimal
    final_amount: Decimal


def route_payment(
    asset: Asset,
    network: Network,
    amount: Decimal,
    settlement_asset: Optional[Asset] = None,
) -> RoutingResult:
    adapter = get_adapter(network)
    network_fee = adapter.estimate_fee(amount)

    amount_after_network_fee = amount - network_fee
    if amount_after_network_fee <= 0:
        raise RoutingError("Amount is too small to cover the network fee")

    settlement_asset = settlement_asset or asset

    gross_converted, conversion_rate, conversion_fee = exchange_provider.convert(
        amount_after_network_fee, asset, settlement_asset
    )

    platform_fee = (gross_converted * PLATFORM_FEE_RATE).quantize(Decimal("0.00000001"))
    final_amount = gross_converted - conversion_fee - platform_fee

    if final_amount <= 0:
        raise RoutingError("Amount is too small to cover network, conversion, and platform fees")

    return RoutingResult(
        source_asset=asset,
        source_network=network,
        settlement_asset=settlement_asset,
        network_fee=network_fee,
        conversion_rate=conversion_rate,
        conversion_fee=conversion_fee,
        platform_fee=platform_fee,
        final_amount=final_amount,
    )
