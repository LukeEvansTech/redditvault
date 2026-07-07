"""Tests for OAuth authentication routes."""


def test_login_redirect(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 302
    assert "reddit.com" in resp.headers["Location"]


def test_login_already_authenticated(auth_client):
    resp = auth_client.get("/auth/login")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_callback_missing_state(client):
    resp = client.get("/auth/callback?code=test")
    assert resp.status_code == 302  # Redirects to index with flash


def test_callback_error_param(client):
    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"
    resp = client.get("/auth/callback?state=test-state&error=access_denied")
    assert resp.status_code == 302


def test_logout_requires_login(client):
    resp = client.get("/auth/logout")
    assert resp.status_code in (302, 401)


def test_logout_authenticated(auth_client):
    resp = auth_client.get("/auth/logout")
    assert resp.status_code == 302
