from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, decode_token


def test_register_user(client):
    resp = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "StrongPass123", "full_name": "Alice"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["verification_state"] == "UNVERIFIED"
    assert "hashed_password" not in body


def test_register_duplicate_email_fails(client):
    payload = {"email": "bob@example.com", "password": "StrongPass123"}
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 400


def test_login_success(client):
    client.post(
        "/auth/register", json={"email": "carol@example.com", "password": "StrongPass123"}
    )
    resp = client.post(
        "/auth/login", json={"email": "carol@example.com", "password": "StrongPass123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_invalid_password_fails(client):
    client.post(
        "/auth/register", json={"email": "dave@example.com", "password": "StrongPass123"}
    )
    resp = client.post(
        "/auth/login", json={"email": "dave@example.com", "password": "WrongPassword"}
    )
    assert resp.status_code == 401


def test_login_nonexistent_user_fails(client):
    resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert resp.status_code == 401


def test_password_is_hashed_not_stored_plaintext():
    plain = "StrongPass123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_roundtrip():
    token = create_access_token(subject="user-123")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_jwt_invalid_token_rejected():
    assert decode_token("not-a-real-token") is None


def test_protected_endpoint_requires_auth(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_protected_endpoint_with_valid_token(client, register_and_login):
    headers, email = register_and_login("erin@example.com")
    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == email


def test_email_verification_flow(client, db_session):
    client.post(
        "/auth/register", json={"email": "frank@example.com", "password": "StrongPass123"}
    )
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "frank@example.com").first()
    token = user.email_verification_token
    assert token is not None

    resp = client.post("/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert resp.json()["verification_state"] == "EMAIL_VERIFIED"


def test_email_verification_invalid_token_fails(client):
    resp = client.post("/auth/verify-email", json={"token": "bogus-token"})
    assert resp.status_code == 400
