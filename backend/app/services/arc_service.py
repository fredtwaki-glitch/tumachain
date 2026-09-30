"""Arc Testnet integration helpers.

This module is intentionally small and dependency-light: Arc exposes an
Ethereum-compatible JSON-RPC endpoint, so the application can query chain
metadata and native USDC balances without adding a blockchain SDK.

Development only: transaction signing is performed by the user's browser
wallet (for example MetaMask), never by the TumaChain server.
"""
from decimal import Decimal
import re
from typing import Any

import httpx

from app.config import settings

ARC_TESTNET_CHAIN_ID = 5042002
ARC_TESTNET_RPC = "https://rpc.testnet.arc.io"
ARC_TESTNET_EXPLORER = "https://explorer.testnet.arc.io"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def arc_config() -> dict[str, Any]:
    return {
        "network": "Arc Testnet",
        "chain_id": settings.arc_chain_id,
        "rpc_url": settings.arc_rpc_url,
        "explorer_url": settings.arc_explorer_url,
        "currency": "USDC",
        "decimals": 18,
        "testnet": True,
        "mode": settings.blockchain_mode,
    }


def validate_evm_address(address: str) -> bool:
    return bool(ADDRESS_RE.fullmatch(address or ""))


def _rpc(method: str, params: list[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    with httpx.Client(timeout=12.0) as client:
        response = client.post(settings.arc_rpc_url, json=payload)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Arc RPC error"))
    return data.get("result")


def get_arc_status() -> dict[str, Any]:
    block_hex = _rpc("eth_blockNumber", [])
    chain_hex = _rpc("eth_chainId", [])
    return {
        **arc_config(),
        "rpc_reachable": True,
        "latest_block": int(block_hex, 16),
        "rpc_chain_id": int(chain_hex, 16),
    }


def get_native_usdc_balance(address: str) -> dict[str, Any]:
    if not validate_evm_address(address):
        raise ValueError("Invalid EVM wallet address")
    result = _rpc("eth_getBalance", [address, "latest"])
    raw = int(result, 16)
    balance = Decimal(raw) / (Decimal(10) ** 18)
    return {
        "address": address,
        "asset": "USDC",
        "network": "ARC_TESTNET",
        "balance": str(balance),
        "raw_balance": str(raw),
        "decimals": 18,
        "explorer_url": f"{settings.arc_explorer_url}/address/{address}",
    }
