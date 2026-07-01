import json

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, cache_manager
from app.storage.db import init_db

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client():
    get_settings.cache_clear()
    init_db()
    cache_manager.clear()
    with TestClient(app) as c:
        yield c


def _collect_events(response) -> list[str]:
    body = "".join(response.iter_text())
    return [line[len("data: "):] for line in body.split("\n") if line.startswith("data: ")]


def _payload(prompt: str) -> dict:
    return {
        "model": "auto",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }


def test_stream_requires_auth(client):
    resp = client.post("/v1/chat/completions", json=_payload("hello"))
    assert resp.status_code == 401


def test_stream_returns_event_stream(client):
    with client.stream(
        "POST", "/v1/chat/completions", json=_payload("stream me a short answer"), headers=HEADERS
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = _collect_events(resp)

    assert events[-1] == "[DONE]"
    chunks = [json.loads(e) for e in events[:-1]]
    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    assert chunks[0]["choices"][0]["delta"].get("role") == "assistant"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


def test_stream_content_matches_non_stream(client):
    prompt = "compare stream and non-stream output"
    non_stream = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": prompt}]},
        headers=HEADERS,
    )
    assert non_stream.status_code == 200
    expected = non_stream.json()["choices"][0]["message"]["content"]

    cache_manager.clear()
    with client.stream(
        "POST", "/v1/chat/completions", json=_payload(prompt), headers=HEADERS
    ) as resp:
        events = _collect_events(resp)

    chunks = [json.loads(e) for e in events[:-1]]
    streamed = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert streamed == expected


def test_stream_final_chunk_reports_usage_and_routing(client):
    with client.stream(
        "POST", "/v1/chat/completions", json=_payload("usage check please"), headers=HEADERS
    ) as resp:
        events = _collect_events(resp)

    final = json.loads(events[-2])
    assert final["usage"]["total_tokens"] > 0
    assert final["route_reason"]
    assert final["cache_status"] == "miss"
    assert final["trace_id"]


def test_stream_serves_cache_hits(client):
    prompt = "cache this streamed answer"
    with client.stream(
        "POST", "/v1/chat/completions", json=_payload(prompt), headers=HEADERS
    ) as resp:
        first_events = _collect_events(resp)
    assert json.loads(first_events[-2])["cache_status"] == "miss"

    with client.stream(
        "POST", "/v1/chat/completions", json=_payload(prompt), headers=HEADERS
    ) as resp:
        second_events = _collect_events(resp)

    final = json.loads(second_events[-2])
    assert final["cache_status"] == "exact_hit"

    first_content = "".join(
        json.loads(e)["choices"][0]["delta"].get("content", "") for e in first_events[:-1]
    )
    second_content = "".join(
        json.loads(e)["choices"][0]["delta"].get("content", "") for e in second_events[:-1]
    )
    assert second_content == first_content
