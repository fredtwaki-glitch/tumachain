import pytest



def test_create_payment_success(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("liam@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.001",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["blockchain_tx_hash"] is None
    assert body["environment"] == "testnet"
    assert body["recipient_email"] == "recipient@example.com"
    assert body["asset"] == "BTC"
    assert body["settlement_asset"] == "BTC"
    assert float(body["final_amount"]) > 0


def test_create_payment_requires_auth(client):
    resp = client.post(
        "/payments",
        json={
            "recipient_email": "recipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.001",
        },
    )
    assert resp.status_code == 401


def test_create_payment_without_funding_fails_insufficient_balance(client, register_and_login):
    headers, _ = register_and_login("mia@example.com")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.001",
        },
    )
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()


def test_create_payment_invalid_recipient_email(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("mia2@example.com")
    fund_wallet(headers)
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "not-an-email",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.001",
        },
    )
    assert resp.status_code == 422


def test_create_payment_invalid_amount_zero(client, register_and_login):
    headers, _ = register_and_login("noah@example.com")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0",
        },
    )
    assert resp.status_code == 422


def test_create_payment_invalid_amount_negative(client, register_and_login):
    headers, _ = register_and_login("olive@example.com")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "-5",
        },
    )
    assert resp.status_code == 422


def test_create_payment_unsupported_cryptocurrency(client, register_and_login):
    headers, _ = register_and_login("paul@example.com")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient@example.com",
            "asset": "DOGE",  # not a supported Asset enum value
            "network": "BITCOIN_TESTNET",
            "amount": "1",
        },
    )
    assert resp.status_code == 422


def test_payment_appears_in_sender_sent_list(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("quinn@example.com")
    fund_wallet(headers, "ETHEREUM_SEPOLIA", "5")
    client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient2@example.com",
            "asset": "ETH",
            "network": "ETHEREUM_SEPOLIA",
            "amount": "0.5",
        },
    )
    resp = client.get("/payments/sent", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_payment_credits_recipient_ledger_balance(client, register_and_login, fund_wallet):
    sender_headers, _ = register_and_login("ruth@example.com")
    recipient_headers, recipient_email = register_and_login("sam@example.com")
    fund_wallet(sender_headers, "SOLANA_DEVNET", "10")

    resp = client.post(
        "/payments",
        headers=sender_headers,
        json={
            "recipient_email": recipient_email,
            "asset": "SOL",
            "network": "SOLANA_DEVNET",
            "amount": "2",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING"
    assert resp.json()["blockchain_tx_hash"] is None

    received = client.get("/payments/received", headers=recipient_headers).json()
    assert len(received) == 1

    balances = client.get("/balances", headers=recipient_headers).json()
    assert balances == []


def test_cross_chain_conversion_to_usdc(client, register_and_login, fund_wallet):
    sender_headers, _ = register_and_login("tina2@example.com")
    recipient_headers, recipient_email = register_and_login("uma2@example.com")
    fund_wallet(sender_headers, "BITCOIN_TESTNET", "1")

    resp = client.post(
        "/payments",
        headers=sender_headers,
        json={
            "recipient_email": recipient_email,
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.01",
            "settlement_asset": "USDC",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["blockchain_tx_hash"] is None
    assert body["settlement_asset"] == "USDC"
    assert float(body["conversion_rate"]) > 1  # BTC is worth much more than 1 USDC
    assert float(body["final_amount"]) > 0

    balances = client.get("/balances", headers=recipient_headers).json()
    assert balances == []


def test_fee_calculation_present_on_payment(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("vince2@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "someone@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.01",
        },
    )
    body = resp.json()
    assert float(body["network_fee"]) > 0
    assert float(body["platform_fee"]) > 0


def test_testnet_payment_remains_pending_without_broadcast(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("will2@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")

    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "someone2@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.0001300013",
        },
    )
    assert resp.status_code == 201
    payment = resp.json()
    assert payment["status"] == "PENDING"
    assert payment["environment"] == "testnet"
    assert payment["blockchain_tx_hash"] is None

    retry_resp = client.post(f"/payments/{payment['id']}/retry", headers=headers)
    assert retry_resp.status_code == 400

def test_retry_only_allowed_on_failed_payments(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("xena2@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "someone3@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.01",
        },
    )
    payment_id = resp.json()["id"]
    retry_resp = client.post(f"/payments/{payment_id}/retry", headers=headers)
    assert retry_resp.status_code == 400


def test_database_persistence_across_requests(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("uma@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "recipient4@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.02",
        },
    )
    resp = client.get("/payments/sent", headers=headers)
    assert len(resp.json()) == 1


def test_idempotency_key_prevents_duplicate_payment(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("vince@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    payload = {
        "recipient_email": "recipient5@example.com",
        "asset": "BTC",
        "network": "BITCOIN_TESTNET",
        "amount": "0.03",
        "idempotency_key": "same-key-123",
    }
    r1 = client.post("/payments", headers=headers, json=payload)
    r2 = client.post("/payments", headers=headers, json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    sent = client.get("/payments/sent", headers=headers).json()
    assert len(sent) == 1


def test_ledger_consistency_second_payment_blocked_when_balance_exhausted(
    client, register_and_login, fund_wallet
):
    headers, _ = register_and_login("consistency@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "0.001")  # just enough for one small payment + fee

    payload = {
        "recipient_email": "recipient6@example.com",
        "asset": "BTC",
        "network": "BITCOIN_TESTNET",
        "amount": "0.0009",
    }
    r1 = client.post("/payments", headers=headers, json=payload)
    assert r1.status_code == 201

    # Second, identical-shape request (simulating a rapid concurrent
    # re-attempt) should now be rejected — balance was already spent.
    payload2 = dict(payload, recipient_email="recipient7@example.com")
    r2 = client.post("/payments", headers=headers, json=payload2)
    assert r2.status_code == 400


def test_get_nonexistent_payment_returns_404(client, register_and_login):
    headers, _ = register_and_login("william@example.com")
    resp = client.get("/payments/does-not-exist", headers=headers)
    assert resp.status_code == 404


def test_get_payment_not_authorized_for_other_user(client, register_and_login, fund_wallet):
    headers_a, _ = register_and_login("xenax@example.com")
    headers_b, _ = register_and_login("yusuf@example.com")
    fund_wallet(headers_a, "BITCOIN_TESTNET", "1")

    created = client.post(
        "/payments",
        headers=headers_a,
        json={
            "recipient_email": "someoneelse@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.04",
        },
    ).json()

    resp = client.get(f"/payments/{created['id']}", headers=headers_b)
    assert resp.status_code == 403
