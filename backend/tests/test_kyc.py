def test_kyc_submission_requires_auth(client):
    resp = client.post(
        "/kyc/submit",
        json={
            "full_name": "Jane Doe",
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    )
    assert resp.status_code == 401


def test_kyc_submission_success(client, register_and_login):
    headers, _ = register_and_login("kycuser1@example.com")
    resp = client.post(
        "/kyc/submit",
        headers=headers,
        json={
            "full_name": "Jane Doe",
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING"

    mine = client.get("/kyc/mine", headers=headers).json()
    assert len(mine) == 1


def test_kyc_duplicate_pending_submission_rejected(client, register_and_login):
    headers, _ = register_and_login("kycuser2@example.com")
    payload = {
        "full_name": "Jane Doe",
        "country": "KE",
        "document_type": "passport",
        "document_reference": "DOC123",
    }
    r1 = client.post("/kyc/submit", headers=headers, json=payload)
    r2 = client.post("/kyc/submit", headers=headers, json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 400


def test_kyc_approval_requires_admin_or_compliance_role(client, register_and_login):
    headers, _ = register_and_login("kycuser3@example.com")
    submit = client.post(
        "/kyc/submit",
        headers=headers,
        json={
            "full_name": "Jane Doe",
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    ).json()

    # A regular user (not admin/compliance) cannot approve.
    resp = client.post(f"/admin/kyc/{submit['id']}/approve", headers=headers)
    assert resp.status_code == 403


def test_kyc_approval_verifies_user(client, register_and_login, admin_headers):
    headers, email = register_and_login("kycuser4@example.com")
    submit = client.post(
        "/kyc/submit",
        headers=headers,
        json={
            "full_name": "Jane Doe",
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    ).json()

    resp = client.post(f"/admin/kyc/{submit['id']}/approve", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    profile = client.get("/users/me", headers=headers).json()
    assert profile["verification_state"] == "KYC_VERIFIED"


def test_kyc_rejection_sets_user_rejected_state(client, register_and_login, admin_headers):
    headers, _ = register_and_login("kycuser5@example.com")
    submit = client.post(
        "/kyc/submit",
        headers=headers,
        json={
            "full_name": "Jane Doe",
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    ).json()

    resp = client.post(
        f"/admin/kyc/{submit['id']}/reject",
        headers=admin_headers,
        json={"reason": "Document unreadable"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["rejection_reason"] == "Document unreadable"

    profile = client.get("/users/me", headers=headers).json()
    assert profile["verification_state"] == "KYC_REJECTED"


def test_kyc_sanctions_hit_blocks_approval(client, register_and_login, admin_headers):
    headers, _ = register_and_login("kycuser6@example.com")
    submit = client.post(
        "/kyc/submit",
        headers=headers,
        json={
            "full_name": "Sanctioned Test Person",  # reserved sentinel name
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    ).json()

    # Even an explicit approve attempt is auto-rejected by the sanctions screen.
    resp = client.post(f"/admin/kyc/{submit['id']}/approve", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

    profile = client.get("/users/me", headers=headers).json()
    assert profile["verification_state"] == "KYC_REJECTED"


def test_kyc_cannot_review_already_reviewed_submission(client, register_and_login, admin_headers):
    headers, _ = register_and_login("kycuser7@example.com")
    submit = client.post(
        "/kyc/submit",
        headers=headers,
        json={
            "full_name": "Jane Doe",
            "country": "KE",
            "document_type": "passport",
            "document_reference": "DOC123",
        },
    ).json()
    client.post(f"/admin/kyc/{submit['id']}/approve", headers=admin_headers)

    resp = client.post(f"/admin/kyc/{submit['id']}/approve", headers=admin_headers)
    assert resp.status_code == 400
