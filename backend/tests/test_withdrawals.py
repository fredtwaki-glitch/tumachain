def _seed_ledger_for_withdrawal(db_session, user_id, asset):
    from decimal import Decimal
    from app.models.enums import Asset
    from app.services.ledger_service import credit_ledger_balance

    credit_ledger_balance(db_session, user_id, Asset(asset), Decimal("0.05"))


def _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, asset="BTC"):
    """Seed an internal ledger balance for withdrawal tests.

    V2 testnet payments remain PENDING until a real/provider-backed
    confirmation exists, so these tests do not depend on fake confirmation.
    """
    _, _ = register_and_login(f"withdrawsender_{asset}@example.com")
    recipient_headers, recipient_email = register_and_login(f"withdrawrecipient_{asset}@example.com")

    from app.models.user import User
    user = db_session.query(User).filter(User.email == recipient_email).first()
    _seed_ledger_for_withdrawal(db_session, user.id, asset)
    return recipient_headers, recipient_email

def test_withdrawal_requires_auth(client):
    resp = client.post(
        "/withdrawals",
        json={
            "asset": "BTC",
            "destination_network": "BITCOIN_TESTNET",
            "destination_address": "tb1mockdeadbeef",
            "amount": "0.01",
        },
    )
    assert resp.status_code == 401


def test_withdrawal_blocked_without_kyc(client, register_and_login, fund_wallet, db_session):
    headers, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "BTC")
    # Deliberately skip KYC verification here.
    resp = client.post(
        "/withdrawals",
        headers=headers,
        json={
            "asset": "BTC",
            "destination_network": "BITCOIN_TESTNET",
            "destination_address": "tb1mockdeadbeefcafebabe",
            "amount": "0.01",
        },
    )
    assert resp.status_code == 400
    assert "kyc" in resp.json()["detail"].lower()


def test_withdrawal_success(client, register_and_login, fund_wallet, kyc_verify, db_session):
    headers, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "BTC")
    kyc_verify(headers)

    balances = client.get("/balances", headers=headers).json()
    btc_balance = next(b for b in balances if b["asset"] == "BTC")
    withdraw_amount = str(float(btc_balance["amount"]) * 0.5)

    resp = client.post(
        "/withdrawals",
        headers=headers,
        json={
            "asset": "BTC",
            "destination_network": "BITCOIN_TESTNET",
            "destination_address": "tb1mockdeadbeefcafebabe",
            "amount": withdraw_amount,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] in {"PENDING", "PROCESSING"}
    assert body["blockchain_tx_hash"] is None
    assert float(body["network_fee"]) > 0


def test_withdrawal_invalid_destination_address(client, register_and_login, fund_wallet, kyc_verify, db_session):
    headers, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "ETH")
    kyc_verify(headers)

    resp = client.post(
        "/withdrawals",
        headers=headers,
        json={
            "asset": "ETH",
            "destination_network": "ETHEREUM_SEPOLIA",
            "destination_address": "not-a-valid-address",
            "amount": "0.01",
        },
    )
    assert resp.status_code == 400
    assert "address" in resp.json()["detail"].lower()


def test_withdrawal_insufficient_balance(client, register_and_login, kyc_verify):
    headers, _ = register_and_login("nofundswithdraw@example.com")
    kyc_verify(headers)
    resp = client.post(
        "/withdrawals",
        headers=headers,
        json={
            "asset": "BTC",
            "destination_network": "BITCOIN_TESTNET",
            "destination_address": "tb1mockdeadbeefcafebabe",
            "amount": "1",
        },
    )
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()


def test_withdrawal_below_minimum_amount(client, register_and_login, fund_wallet, kyc_verify, db_session):
    headers, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "SOL")
    kyc_verify(headers)
    resp = client.post(
        "/withdrawals",
        headers=headers,
        json={
            "asset": "SOL",
            "destination_network": "SOLANA_DEVNET",
            "destination_address": "MOCKSOLdeadbeefcafebabe",
            "amount": "0.00000001",
        },
    )
    assert resp.status_code == 400
    assert "minimum" in resp.json()["detail"].lower()


def test_withdrawal_idempotency(client, register_and_login, fund_wallet, kyc_verify, db_session):
    headers, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "EVMT")
    kyc_verify(headers)
    payload = {
        "asset": "EVMT",
        "destination_network": "EVM_TESTNET",
        "destination_address": "0xMOCKEVMdeadbeefcafebabe",
        "amount": "0.01",
        "idempotency_key": "withdraw-key-1",
    }
    r1 = client.post("/withdrawals", headers=headers, json=payload)
    r2 = client.post("/withdrawals", headers=headers, json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    listing = client.get("/withdrawals", headers=headers).json()
    assert len(listing) == 1


def test_withdrawal_list_and_get(client, register_and_login, fund_wallet, kyc_verify, db_session):
    headers, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "BTC")
    kyc_verify(headers)
    created = client.post(
        "/withdrawals",
        headers=headers,
        json={
            "asset": "BTC",
            "destination_network": "BITCOIN_TESTNET",
            "destination_address": "tb1mockdeadbeefcafebabe2",
            "amount": "0.01",
        },
    ).json()

    listing = client.get("/withdrawals", headers=headers).json()
    assert any(w["id"] == created["id"] for w in listing)

    single = client.get(f"/withdrawals/{created['id']}", headers=headers)
    assert single.status_code == 200
    assert single.json()["id"] == created["id"]


def test_withdrawal_not_visible_to_other_users(client, register_and_login, fund_wallet, kyc_verify, db_session):
    headers_a, _ = _complete_a_payment_to_fund_ledger(client, register_and_login, fund_wallet, db_session, "BTC")
    kyc_verify(headers_a)
    headers_b, _ = register_and_login("otherwithdrawuser@example.com")

    created = client.post(
        "/withdrawals",
        headers=headers_a,
        json={
            "asset": "BTC",
            "destination_network": "BITCOIN_TESTNET",
            "destination_address": "tb1mockdeadbeefcafebabe3",
            "amount": "0.01",
        },
    ).json()

    resp = client.get(f"/withdrawals/{created['id']}", headers=headers_b)
    assert resp.status_code == 403
