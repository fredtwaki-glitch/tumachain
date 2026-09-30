def test_admin_endpoint_rejects_regular_user(client, register_and_login):
    headers, _ = register_and_login("regularuser@example.com")
    resp = client.get("/admin/summary", headers=headers)
    assert resp.status_code == 403


def test_admin_endpoint_rejects_unauthenticated(client):
    resp = client.get("/admin/summary")
    assert resp.status_code == 401


def test_admin_endpoint_allows_admin(client, register_and_login, db_session):
    headers, email = register_and_login("adminuser@example.com")

    from app.models.enums import UserRole
    from app.models.user import User

    user = db_session.query(User).filter(User.email == email).first()
    user.role = UserRole.ADMIN
    db_session.commit()

    resp = client.get("/admin/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "users" in body
    assert body["mode"] == "TESTNET/SIMULATED"
