import pytest


def test_large_transaction_is_held_for_review(client, register_and_login, fund_wallet):
    headers, _ = register_and_login("largetx@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")

    # 0.1 BTC * $60000 mock rate = $6000, over the $5000 large-tx threshold.
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "largetxrecipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.1",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["held_for_review"] is True
    assert body["is_flagged"] is True
    assert "large transaction" in body["flag_reason"].lower()


def test_unverified_user_hits_low_daily_limit(client, fund_wallet):
    # Register + login WITHOUT verifying email, so the account stays UNVERIFIED.
    client.post(
        "/auth/register",
        json={"email": "unverifieduser@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/auth/login", json={"email": "unverifieduser@example.com", "password": "StrongPass123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    fund_wallet(headers, "BITCOIN_TESTNET", "1")

    # 0.002 BTC = $120, over the $100 UNVERIFIED daily limit but well under
    # the $5000 large-transaction threshold, isolating the daily-limit reason.
    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "unverifiedrecipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.002",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["held_for_review"] is True
    assert "daily transaction limit" in body["flag_reason"].lower()


def test_suspended_account_cannot_create_payment(client, register_and_login, fund_wallet, admin_headers):
    headers, email = register_and_login("suspendme@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")

    users = client.get("/admin/users", headers=admin_headers).json()
    target = next(u for u in users if u["email"] == email)

    suspend_resp = client.post(
        f"/admin/users/{target['id']}/suspend",
        headers=admin_headers,
        json={"reason": "Suspicious activity"},
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["verification_state"] == "SUSPENDED"

    resp = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "someone@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.001",
        },
    )
    assert resp.status_code == 400
    assert "suspend" in resp.json()["detail"].lower()


def test_suspend_requires_admin_role(client, register_and_login):
    headers, _ = register_and_login("notanadmin@example.com")
    users = client.get("/admin/users", headers=headers)
    assert users.status_code == 403


def test_unsuspend_restores_account(client, register_and_login, admin_headers):
    headers, email = register_and_login("unsuspendme@example.com")
    users = client.get("/admin/users", headers=admin_headers).json()
    target = next(u for u in users if u["email"] == email)

    client.post(
        f"/admin/users/{target['id']}/suspend", headers=admin_headers, json={"reason": "test"}
    )
    resp = client.post(f"/admin/users/{target['id']}/unsuspend", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["verification_state"] != "SUSPENDED"
    assert resp.json()["is_active"] is True


def test_admin_release_held_payment(client, register_and_login, fund_wallet, admin_headers):
    headers, _ = register_and_login("releasepay@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")

    created = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "releaserecipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.1",  # large tx -> held
        },
    ).json()
    assert created["held_for_review"] is True

    resp = client.post(f"/admin/payments/{created['id']}/release", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"
    assert resp.json()["blockchain_tx_hash"] is None
    assert resp.json()["held_for_review"] is False


def test_admin_reject_held_payment_refunds_sender(client, register_and_login, fund_wallet, admin_headers):
    headers, _ = register_and_login("rejectpay@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")

    created = client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "rejectrecipient@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.1",  # large tx -> held
        },
    ).json()

    resp = client.post(
        f"/admin/payments/{created['id']}/reject",
        headers=admin_headers,
        json={"reason": "Failed manual review"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"

    wallets = client.get("/wallets", headers=headers).json()
    btc_wallet = next(w for w in wallets if w["network"] == "BITCOIN_TESTNET")
    assert float(btc_wallet["balance"]) == pytest.approx(1.0)


def test_flagged_payments_listing(client, register_and_login, fund_wallet, admin_headers):
    headers, _ = register_and_login("flaggeduser@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "x@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.1",
        },
    )
    resp = client.get("/admin/flagged/payments", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_audit_logs_recorded_and_listable(client, register_and_login, fund_wallet, admin_headers):
    headers, _ = register_and_login("audituser@example.com")
    fund_wallet(headers, "BITCOIN_TESTNET", "1")
    client.post(
        "/payments",
        headers=headers,
        json={
            "recipient_email": "y@example.com",
            "asset": "BTC",
            "network": "BITCOIN_TESTNET",
            "amount": "0.1",
        },
    )
    resp = client.get("/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    actions = [log["action"] for log in resp.json()]
    assert "PAYMENT_HELD" in actions


def test_audit_logs_require_admin(client, register_and_login):
    headers, _ = register_and_login("notadminaudit@example.com")
    resp = client.get("/admin/audit-logs", headers=headers)
    assert resp.status_code == 403
