"""Tests for API routes."""

import json


def test_stats_unauthenticated(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 401


def test_stats_with_api_key(client, api_key, saved_item):
    raw_key, _ = api_key
    resp = client.get("/api/stats", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1


def test_stats_with_session(auth_client, saved_item):
    resp = auth_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total" in data


def test_update_item_state(auth_client, saved_item):
    resp = auth_client.post(
        f"/api/item/{saved_item.reddit_id}/state",
        data=json.dumps({"reviewed": True}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["state"]["reviewed"] is True


def test_update_item_state_not_found(auth_client):
    resp = auth_client.post(
        "/api/item/nonexistent/state",
        data=json.dumps({"reviewed": True}),
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_sync_status(auth_client):
    resp = auth_client.get("/api/sync/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "sync_in_progress" in data


def test_invalid_api_key(client):
    resp = client.get("/api/stats", headers={"Authorization": "Bearer bad-key"})
    assert resp.status_code == 401


def test_api_key_via_x_api_key_header(client, api_key):
    raw_key, _ = api_key
    resp = client.get("/api/stats", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
