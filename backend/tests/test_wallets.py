def test_wallets_created_on_registration(client, register_and_login):
    headers, _ = register_and_login("gina@example.com")
    resp = client.get("/wallets", headers=headers)
    assert resp.status_code == 200
    wallets = resp.json()
    assert len(wallets) == 5  # BTC, ETH, SOL, EVM testnet, Arc testnet
    networks = {w["network"] for w in wallets}
    assert networks == {
        "BITCOIN_TESTNET",
        "ETHEREUM_SEPOLIA",
        "SOLANA_DEVNET",
        "EVM_TESTNET",
        "ARC_TESTNET",
    }


def test_wallet_addresses_are_mock_prefixed(client, register_and_login):
    headers, _ = register_and_login("henry@example.com")
    resp = client.get("/wallets", headers=headers)
    wallets = resp.json()
    for w in wallets:
        assert "MOCK" in w["address"].upper()


def test_wallet_private_key_never_exposed(client, register_and_login):
    headers, _ = register_and_login("ivy@example.com")
    resp = client.get("/wallets", headers=headers)
    body_text = resp.text.lower()
    assert "private_key" not in body_text
    assert "mockkey_" not in body_text


def test_wallet_isolation_between_users(client, register_and_login):
    headers_a, _ = register_and_login("judy@example.com")
    headers_b, _ = register_and_login("kyle@example.com")

    wallets_a = client.get("/wallets", headers=headers_a).json()
    wallets_b = client.get("/wallets", headers=headers_b).json()

    addresses_a = {w["address"] for w in wallets_a}
    addresses_b = {w["address"] for w in wallets_b}

    # No overlap in addresses between users' wallets.
    assert addresses_a.isdisjoint(addresses_b)

    # A user cannot see another user's wallets via their own token.
    resp = client.get("/wallets", headers=headers_a)
    for w in resp.json():
        assert w["address"] in addresses_a
        assert w["address"] not in addresses_b


def test_faucet_credits_balance(client, register_and_login):
    headers, _ = register_and_login("faucetuser@example.com")
    resp = client.post(
        "/wallets/faucet", headers=headers, json={"network": "BITCOIN_TESTNET", "amount": "2.5"}
    )
    assert resp.status_code == 200
    assert float(resp.json()["balance"]) == 2.5


def test_faucet_requires_auth(client):
    resp = client.post(
        "/wallets/faucet", json={"network": "BITCOIN_TESTNET", "amount": "1"}
    )
    assert resp.status_code == 401


def test_new_user_has_no_ledger_balances_yet(client, register_and_login):
    headers, _ = register_and_login("emptyledger@example.com")
    resp = client.get("/balances", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []
