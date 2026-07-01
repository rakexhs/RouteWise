import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.storage.db import init_db

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client():
    get_settings.cache_clear()
    init_db()
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_models_requires_auth(client):
    resp = client.get("/v1/models")
    assert resp.status_code == 401


def test_models_list(client):
    resp = client.get("/v1/models", headers=HEADERS)
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()["data"]]
    assert "mock-small" in ids
    assert "auto" in ids


def test_chat_completion_auto(client):
    resp = client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "Say hello"}],
            "metadata": {"feature": "test"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "choices" in data
    assert data["cache_status"] in ("miss", "exact_hit", "semantic_hit")
    assert "route_reason" in data
    assert "trace_id" in data


def test_exact_cache_hit(client):
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "Unique cache test prompt xyz123"}],
    }
    r1 = client.post("/v1/chat/completions", headers=HEADERS, json=payload)
    r2 = client.post("/v1/chat/completions", headers=HEADERS, json=payload)
    assert r1.json()["cache_status"] == "miss"
    assert r2.json()["cache_status"] == "exact_hit"


def test_pii_redaction_in_logs(client):
    email = "secret.user@example.com"
    client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": f"My email is {email}"}],
        },
    )
    resp = client.get("/admin/requests", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.text
    assert email not in body


def test_metrics_endpoint(client):
    client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"model": "mock-small", "messages": [{"role": "user", "content": "metrics"}]},
    )
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "routewise_requests_total" in resp.text


def test_admin_costs(client):
    resp = client.get("/admin/costs", headers=HEADERS)
    assert resp.status_code == 200
    assert "daily_spend" in resp.json()


def test_stream_returns_sse(client):
    resp = client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
