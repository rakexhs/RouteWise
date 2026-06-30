import pytest
from sqlalchemy.orm import Session

from app.gateway.router import decide_route, estimate_complexity, prompt_hash
from app.providers import ProviderRegistry
from app.storage.db import get_session_factory, init_db


@pytest.fixture
def session():
    init_db()
    s = get_session_factory()()
    yield s
    s.close()


@pytest.fixture
def registry():
    return ProviderRegistry()


def test_explicit_route(registry, session):
    decision = decide_route(
        model="mock-large",
        messages=[{"role": "user", "content": "hi"}],
        registry=registry,
        session=session,
    )
    assert decision.model_id == "mock-large"
    assert decision.route_reason == "explicit_model"


def test_auto_simple_route(registry, session):
    decision = decide_route(
        model="auto",
        messages=[{"role": "user", "content": "Hi"}],
        registry=registry,
        session=session,
    )
    assert decision.model_id == "mock-small"
    assert decision.route_reason == "simple_prompt"


def test_auto_complex_route(registry, session):
    long_prompt = "Explain " + "distributed systems " * 80 + " with code ```python\ndef foo(): pass```"
    decision = decide_route(
        model="auto",
        messages=[{"role": "user", "content": long_prompt}],
        registry=registry,
        session=session,
    )
    assert decision.model_id in ("mock-large", "mock-small")
    assert decision.route_reason in ("complex_prompt", "moderate_prompt")


def test_complexity_score():
    score = estimate_complexity([{"role": "user", "content": "short"}])
    assert 0 <= score.score <= 1


def test_prompt_hash_stable():
    msgs = [{"role": "user", "content": "Hello"}]
    assert prompt_hash(msgs) == prompt_hash(msgs)
