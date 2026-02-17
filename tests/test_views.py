"""Tests for web view routes."""


def test_index_unauthenticated(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"login" in resp.data.lower() or b"Login" in resp.data


def test_index_authenticated(auth_client, saved_item):
    resp = auth_client.get("/")
    assert resp.status_code == 200


def test_category_requires_login(client):
    resp = client.get("/category/test")
    assert resp.status_code in (302, 401)


def test_category_authenticated(auth_client, saved_item):
    resp = auth_client.get("/category/Self-Hosting%20%26%20Homelab")
    assert resp.status_code == 200


def test_search_requires_login(client):
    resp = client.get("/search?q=test")
    assert resp.status_code in (302, 401)


def test_search_empty_query(auth_client):
    resp = auth_client.get("/search")
    assert resp.status_code == 200


def test_search_with_query(auth_client, saved_item):
    resp = auth_client.get("/search?q=Test")
    assert resp.status_code == 200
