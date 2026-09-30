def test_refresh_token_issues_new_pair(client, register_and_login):
    headers, email = register_and_login("refreshuser@example.com")
    login = client.post(
        "/auth/login", json={"email": email, "password": "StrongPass123"}
    ).json()

    resp = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body

    # The new access token actually works.
    new_headers = {"Authorization": f"Bearer {body['access_token']}"}
    profile = client.get("/users/me", headers=new_headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == email


def test_refresh_token_rejects_access_token(client, register_and_login):
    headers, email = register_and_login("refreshuser2@example.com")
    login = client.post(
        "/auth/login", json={"email": email, "password": "StrongPass123"}
    ).json()

    # Passing an access token where a refresh token is expected should fail.
    resp = client.post("/auth/refresh", json={"refresh_token": login["access_token"]})
    assert resp.status_code == 401


def test_refresh_token_rejects_garbage(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


def test_secure_headers_present(client):
    resp = client.get("/")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "referrer-policy" in resp.headers


def test_rate_limiting_blocks_excessive_requests(client):
    from app.config import settings

    limit = settings.rate_limit_requests
    last_status = None
    for _ in range(limit + 5):
        last_status = client.get("/networks").status_code

    assert last_status == 429


def test_rate_limit_exempts_health_and_root(client):
    from app.config import settings

    # Hammer /health well past the limit — it should never be rate-limited.
    for _ in range(settings.rate_limit_requests + 10):
        resp = client.get("/health")
        assert resp.status_code == 200
