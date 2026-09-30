"""
Blockchain abstraction layer.

Phase 2 extends Phase 1's address generation with the transaction
lifecycle: fee estimation, transaction creation, broadcast, and status
lookup. Every method here is fully mocked/simulated — no real chain is
ever contacted. Real adapters (a real BitcoinAdapter using an RPC
client, etc.) would implement this same interface later without
changing any calling code in `services/`.
"""
import hashlib
import secrets
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Tuple

from app.models.enums import Network

# A deterministic "poison" amount used ONLY by the test suite to exercise
# the failure/retry path without needing real network flakiness. Chosen
# to be comfortably larger than any mock network's flat fee (so routing
# doesn't reject it before it ever reaches the broadcast step) but
# distinctive enough that no normal test amount would collide with it.
SIMULATED_BROADCAST_FAILURE_AMOUNT = Decimal("0.0001300013")


class BlockchainAdapter(ABC):
    network: Network

    @abstractmethod
    def generate_address(self, user_id: str) -> Tuple[str, str]:
        """Returns (address, mock_private_key). Never expose the key via the API."""
        raise NotImplementedError

    @abstractmethod
    def validate_address(self, address: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def estimate_fee(self, amount: Decimal) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def create_transaction(self, from_address: str, to_address: str, amount: Decimal) -> str:
        """Returns a mock transaction hash."""
        raise NotImplementedError

    @abstractmethod
    def broadcast_transaction(self, tx_hash: str, amount: Decimal) -> bool:
        """Returns True if the (simulated) broadcast succeeded."""
        raise NotImplementedError

    @abstractmethod
    def get_transaction_status(self, tx_hash: str) -> str:
        raise NotImplementedError

    def get_balance(self, address: str) -> Decimal:
        # Phase 1/2 track balances in the app's own ledger/wallet tables,
        # not on a real chain, so this is a stub for interface completeness.
        return Decimal("0")


class MockBlockchainAdapter(BlockchainAdapter):
    """
    Deterministic, clearly-fake blockchain adapter. Addresses are
    prefixed so it's obvious at a glance they are mock/testnet values,
    never to be used with real funds.
    """

    PREFIXES = {
        Network.BITCOIN_TESTNET: "tb1mock",
        Network.ETHEREUM_SEPOLIA: "0xMOCK",
        Network.SOLANA_DEVNET: "MOCKSOL",
        Network.EVM_TESTNET: "0xMOCKEVM",
        Network.ARC_TESTNET: "0xMOCKARC",
    }

    # Flat, made-up mock network fee per chain (in that chain's own asset).
    FLAT_NETWORK_FEE = {
        Network.BITCOIN_TESTNET: Decimal("0.00005"),
        Network.ETHEREUM_SEPOLIA: Decimal("0.0003"),
        Network.SOLANA_DEVNET: Decimal("0.000005"),
        Network.EVM_TESTNET: Decimal("0.0002"),
        Network.ARC_TESTNET: Decimal("0.0001"),
    }

    def __init__(self, network: Network):
        self.network = network

    def generate_address(self, user_id: str) -> Tuple[str, str]:
        seed = f"{user_id}:{self.network.value}:{secrets.token_hex(8)}"
        digest = hashlib.sha256(seed.encode()).hexdigest()[:32]
        prefix = self.PREFIXES.get(self.network, "MOCK")
        address = f"{prefix}{digest}"
        mock_private_key = f"mockkey_{uuid.uuid4().hex}"
        return address, mock_private_key

    def validate_address(self, address: str) -> bool:
        prefix = self.PREFIXES.get(self.network, "MOCK")
        return isinstance(address, str) and address.startswith(prefix) and len(address) > len(prefix)

    def estimate_fee(self, amount: Decimal) -> Decimal:
        return self.FLAT_NETWORK_FEE.get(self.network, Decimal("0.0001"))

    def create_transaction(self, from_address: str, to_address: str, amount: Decimal) -> str:
        raise RuntimeError("No live blockchain transaction adapter is configured; testnet mode will not fabricate a transaction hash")

    def broadcast_transaction(self, tx_hash: str, amount: Decimal) -> bool:
        raise RuntimeError("Live blockchain broadcasting is not configured in testnet mode")

    def get_transaction_status(self, tx_hash: str) -> str:
        raise RuntimeError("Live blockchain status lookup is not configured in testnet mode")


class BitcoinAdapter(MockBlockchainAdapter):
    def __init__(self):
        super().__init__(Network.BITCOIN_TESTNET)


class EthereumAdapter(MockBlockchainAdapter):
    def __init__(self):
        super().__init__(Network.ETHEREUM_SEPOLIA)


class SolanaAdapter(MockBlockchainAdapter):
    def __init__(self):
        super().__init__(Network.SOLANA_DEVNET)


class ArcTestnetAdapter(MockBlockchainAdapter):
    def __init__(self): super().__init__(Network.ARC_TESTNET)


class EvmTestnetAdapter(MockBlockchainAdapter):
    def __init__(self):
        super().__init__(Network.EVM_TESTNET)


_ADAPTER_CLASSES = {
    Network.BITCOIN_TESTNET: BitcoinAdapter,
    Network.ETHEREUM_SEPOLIA: EthereumAdapter,
    Network.SOLANA_DEVNET: SolanaAdapter,
    Network.EVM_TESTNET: EvmTestnetAdapter,
    Network.ARC_TESTNET: ArcTestnetAdapter,
}


def get_adapter(network: Network) -> BlockchainAdapter:
    # Phase 1/2 always resolve to a mock adapter regardless of configured
    # mode, since real providers are not wired up yet. The per-network
    # class still models the eventual real BitcoinAdapter/EthereumAdapter/
    # SolanaAdapter split so swapping in real implementations later is a
    # drop-in change.
    adapter_cls = _ADAPTER_CLASSES.get(network, MockBlockchainAdapter)
    if adapter_cls is MockBlockchainAdapter:
        return MockBlockchainAdapter(network)
    return adapter_cls()
