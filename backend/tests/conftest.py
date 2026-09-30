import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, get_db  # noqa: E402
from app import models  # noqa: E402,F401
from app.main import app  # noqa: E402

TEST_DATABASE_URL = "sqlite:///./test_pay_via_mail.db"


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The rate limiter's state is module-level (see security/rate_limit.py)
    because the FastAPI app is a singleton across the whole test session.
    Reset it before every test so tests don't leak rate-limit state into
    each other."""
    from app.security.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists("./test_pay_via_mail.db"):
            os.remove("./test_pay_via_mail.db")


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def register_and_login(client, db_session):
    """Registers+logs in a user, auto-verifies their email (so they default
    to EMAIL_VERIFIED rather than UNVERIFIED, matching realistic usage),
    and returns (headers, email)."""

    def _make(email="user@example.com", password="StrongPass123"):
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "full_name": "Test User"},
        )

        from app.models.user import User

        user = db_session.query(User).filter(User.email == email).first()
        if user and user.email_verification_token:
            client.post("/auth/verify-email", json={"token": user.email_verification_token})

        resp = client.post("/auth/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, email

    return _make


@pytest.fixture
def fund_wallet(client):
    """Returns a helper that tops up a user's mock testnet wallet via the faucet."""

    def _fund(headers, network="BITCOIN_TESTNET", amount="10"):
        resp = client.post(
            "/wallets/faucet", headers=headers, json={"network": network, "amount": amount}
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _fund


@pytest.fixture
def admin_headers(client, register_and_login, db_session):
    """Registers a fresh user, promotes them to ADMIN directly via the DB, and
    returns their auth headers — used for admin/compliance-only endpoints."""
    headers, email = register_and_login("admin_reviewer@example.com")

    from app.models.enums import UserRole
    from app.models.user import User

    user = db_session.query(User).filter(User.email == email).first()
    user.role = UserRole.ADMIN
    db_session.commit()

    return headers


@pytest.fixture
def kyc_verify(client, admin_headers):
    """Returns a helper that submits + admin-approves KYC for a given user,
    leaving them in KYC_VERIFIED state."""

    def _verify(user_headers, full_name="Jane Doe", country="KE"):
        submit_resp = client.post(
            "/kyc/submit",
            headers=user_headers,
            json={
                "full_name": full_name,
                "country": country,
                "document_type": "passport",
                "document_reference": "MOCKDOC123",
            },
        )
        assert submit_resp.status_code == 201, submit_resp.text
        submission_id = submit_resp.json()["id"]

        approve_resp = client.post(f"/admin/kyc/{submission_id}/approve", headers=admin_headers)
        assert approve_resp.status_code == 200, approve_resp.text
        return approve_resp.json()

    return _verify
