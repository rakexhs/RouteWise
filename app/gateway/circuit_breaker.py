import json
import time
from enum import Enum
from threading import Lock

from app.config import get_settings
from app.telemetry.metrics import set_circuit_state


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self) -> None:
        self._states: dict[str, CircuitState] = {}
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._lock = Lock()
        self.settings = get_settings()

    def _get_state(self, provider: str) -> CircuitState:
        state = self._states.get(provider, CircuitState.CLOSED)
        if state == CircuitState.OPEN:
            opened = self._opened_at.get(provider, 0)
            if time.time() - opened >= self.settings.circuit_cooldown_seconds:
                self._states[provider] = CircuitState.HALF_OPEN
                set_circuit_state(provider, "half_open")
                return CircuitState.HALF_OPEN
        return state

    def can_execute(self, provider: str) -> bool:
        with self._lock:
            state = self._get_state(provider)
            set_circuit_state(provider, state.value)
            return state != CircuitState.OPEN

    def record_success(self, provider: str) -> None:
        with self._lock:
            self._states[provider] = CircuitState.CLOSED
            self._failures[provider] = 0
            set_circuit_state(provider, "closed")

    def record_failure(self, provider: str) -> None:
        with self._lock:
            failures = self._failures.get(provider, 0) + 1
            self._failures[provider] = failures
            if failures >= self.settings.circuit_failure_threshold:
                self._states[provider] = CircuitState.OPEN
                self._opened_at[provider] = time.time()
                set_circuit_state(provider, "open")
            elif self._states.get(provider) == CircuitState.HALF_OPEN:
                self._states[provider] = CircuitState.OPEN
                self._opened_at[provider] = time.time()
                set_circuit_state(provider, "open")

    def get_states(self) -> dict[str, str]:
        with self._lock:
            return {p: self._get_state(p).value for p in set(self._states) | {"mock-small", "mock-large"}}

    def export_state(self) -> dict[str, dict]:
        with self._lock:
            return {
                provider: {
                    "state": self._get_state(provider).value,
                    "failures": self._failures.get(provider, 0),
                }
                for provider in set(self._states) | {"mock-small", "mock-large", "ollama", "openai", "anthropic"}
            }

    def save_snapshot(self, path: str = "data/circuit_state.json") -> None:
        import os

        os.makedirs("data", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.export_state(), f, indent=2)


circuit_breaker = CircuitBreaker()
