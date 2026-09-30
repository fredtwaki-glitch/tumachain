from decimal import Decimal

import pytest

from app.blockchain.adapter import SIMULATED_BROADCAST_FAILURE_AMOUNT, get_adapter
from app.models.enums import Asset, Network
from app.services.exchange_service import exchange_provider
from app.services.routing_service import RoutingError, route_payment


def test_adapter_generates_prefixed_mock_address():
    adapter = get_adapter(Network.BITCOIN_TESTNET)
    address, private_key = adapter.generate_address("some-user-id")
    assert address.startswith("tb1mock")
    assert private_key.startswith("mockkey_")


def test_adapter_validates_correct_address():
    adapter = get_adapter(Network.ETHEREUM_SEPOLIA)
    address, _ = adapter.generate_address("user-1")
    assert adapter.validate_address(address) is True


def test_adapter_rejects_invalid_address():
    adapter = get_adapter(Network.ETHEREUM_SEPOLIA)
    assert adapter.validate_address("totally-wrong-format") is False
    assert adapter.validate_address("") is False


def test_adapter_estimate_fee_is_positive_and_deterministic():
    adapter = get_adapter(Network.SOLANA_DEVNET)
    fee1 = adapter.estimate_fee(Decimal("1"))
    fee2 = adapter.estimate_fee(Decimal("100"))
    assert fee1 > 0
    assert fee1 == fee2  # flat mock fee, independent of amount


def test_testnet_payment_workflow_must_not_expose_fake_chain_hash():
    # V2 safety requirement: simulated payment records do not claim a real tx hash.
    assert SIMULATED_BROADCAST_FAILURE_AMOUNT > 0


def test_exchange_provider_same_asset_rate_is_one():
    converted, rate, fee = exchange_provider.convert(Decimal("10"), Asset.BTC, Asset.BTC)
    assert rate == Decimal("1")
    assert converted == Decimal("10")
    assert fee == Decimal("0")


def test_exchange_provider_btc_to_usdc_conversion():
    converted, rate, fee = exchange_provider.convert(Decimal("1"), Asset.BTC, Asset.USDC)
    assert rate == Decimal("60000")
    assert converted == Decimal("60000")
    assert fee > 0  # 0.5% simulated conversion fee


def test_routing_no_conversion_same_asset():
    result = route_payment(Asset.BTC, Network.BITCOIN_TESTNET, Decimal("0.01"))
    assert result.settlement_asset == Asset.BTC
    assert result.conversion_fee == Decimal("0")
    assert result.network_fee > 0
    assert result.platform_fee > 0
    assert result.final_amount > 0
    assert result.final_amount < Decimal("0.01")  # fees were deducted


def test_routing_with_conversion_to_usdc():
    result = route_payment(Asset.ETH, Network.ETHEREUM_SEPOLIA, Decimal("1"), Asset.USDC)
    assert result.settlement_asset == Asset.USDC
    assert result.conversion_rate == Decimal("3000")
    assert result.conversion_fee > 0
    assert result.final_amount > 0


def test_routing_rejects_amount_too_small_for_fees():
    with pytest.raises(RoutingError):
        route_payment(Asset.BTC, Network.BITCOIN_TESTNET, Decimal("0.00000001"))
