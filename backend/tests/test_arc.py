from app.services.arc_service import arc_config, validate_evm_address


def test_arc_testnet_configuration():
    cfg = arc_config()
    assert cfg["network"] == "Arc Testnet"
    assert cfg["chain_id"] == 5042002
    assert cfg["rpc_url"] == "https://rpc.testnet.arc.io"
    assert cfg["explorer_url"] == "https://explorer.testnet.arc.io"
    assert cfg["currency"] == "USDC"
    assert cfg["decimals"] == 18


def test_arc_evm_address_validation():
    assert validate_evm_address("0x" + "a" * 40)
    assert not validate_evm_address("0x123")
    assert not validate_evm_address("not-an-address")
