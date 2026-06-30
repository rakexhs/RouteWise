import time

from app.gateway.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_opens_after_failures():
    breaker = CircuitBreaker()
    breaker.settings.circuit_failure_threshold = 3
    breaker.settings.circuit_cooldown_seconds = 1

    for _ in range(3):
        breaker.record_failure("mock-large")

    assert breaker.can_execute("mock-large") is False
    state = breaker.get_states()["mock-large"]
    assert state == CircuitState.OPEN.value


def test_circuit_half_open_then_closed():
    breaker = CircuitBreaker()
    breaker.settings.circuit_failure_threshold = 2
    breaker.settings.circuit_cooldown_seconds = 0.1

    breaker.record_failure("mock-small")
    breaker.record_failure("mock-small")
    assert breaker.can_execute("mock-small") is False

    time.sleep(0.15)
    assert breaker.can_execute("mock-small") is True
    breaker.record_success("mock-small")
    assert breaker.get_states()["mock-small"] == CircuitState.CLOSED.value


def test_circuit_half_open_failure_reopens():
    breaker = CircuitBreaker()
    breaker.settings.circuit_failure_threshold = 1
    breaker.settings.circuit_cooldown_seconds = 0.05
    breaker.record_failure("test-provider")
    time.sleep(0.06)
    breaker.can_execute("test-provider")
    breaker.record_failure("test-provider")
    assert breaker.get_states()["test-provider"] == CircuitState.OPEN.value
