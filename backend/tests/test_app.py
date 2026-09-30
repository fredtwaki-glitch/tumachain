def test_root_serves_landing_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "TESTNET / SIMULATED" in resp.text
    assert 'href="/register"' in resp.text


def test_app_routes_serve_existing_ui(client):
    for path in ("/login", "/register", "/dashboard"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "ARC_TESTNET_UI_MARKER" in resp.text


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_networks_endpoint_lists_supported_assets(client):
    resp = client.get("/networks")
    assert resp.status_code == 200
    body = resp.json()
    assert "BTC" in body["assets"]
    assert "ETH" in body["assets"]
    assert "SOL" in body["assets"]
    assert "USDC" in body["assets"]


def test_malformed_json_returns_422(client):
    resp = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )
    assert resp.status_code == 422


def test_missing_required_field_returns_422(client):
    resp = client.post("/auth/register", json={"email": "zed@example.com"})
    assert resp.status_code == 422


def test_invalid_token_on_protected_route_returns_401(client):
    resp = client.get("/users/me", headers={"Authorization": "Bearer garbage.token.value"})
    assert resp.status_code == 401
