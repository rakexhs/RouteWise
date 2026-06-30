#!/usr/bin/env python3
"""Demo requests against the RouteWise gateway."""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings

BASE = "http://127.0.0.1:8000"


def main() -> None:
    settings = get_settings()
    headers = {"X-API-Key": settings.demo_api_key, "Content-Type": "application/json"}

    with httpx.Client(timeout=30.0) as client:
        print("=== Health ===")
        health = client.get(f"{BASE}/health")
        print(json.dumps(health.json(), indent=2))

        print("\n=== Models ===")
        models = client.get(f"{BASE}/v1/models", headers=headers)
        print(json.dumps(models.json(), indent=2))

        prompt = "Summarize REST APIs in one sentence."
        payload = {
            "model": "auto",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "metadata": {"feature": "demo"},
        }

        print("\n=== Auto route (first request) ===")
        r1 = client.post(f"{BASE}/v1/chat/completions", headers=headers, json=payload)
        d1 = r1.json()
        print(f"model={d1['model']} cache={d1['cache_status']} route={d1['route_reason']}")
        print(f"latency={d1['latency_ms']}ms cost=${d1['estimated_cost']}")
        print(d1["choices"][0]["message"]["content"][:200])

        print("\n=== Auto route (cache warm) ===")
        r2 = client.post(f"{BASE}/v1/chat/completions", headers=headers, json=payload)
        d2 = r2.json()
        print(f"model={d2['model']} cache={d2['cache_status']} route={d2['route_reason']}")
        print(f"latency={d2['latency_ms']}ms cost=${d2['estimated_cost']}")

        print("\n=== Explicit mock-large ===")
        payload["model"] = "mock-large"
        payload["messages"] = [
            {
                "role": "user",
                "content": "Explain circuit breakers in distributed systems with examples.",
            }
        ]
        r3 = client.post(f"{BASE}/v1/chat/completions", headers=headers, json=payload)
        d3 = r3.json()
        print(f"model={d3['model']} route={d3['route_reason']}")
        print(d3["choices"][0]["message"]["content"][:200])

        print("\n=== Metrics sample ===")
        metrics = client.get(f"{BASE}/metrics")
        lines = [l for l in metrics.text.splitlines() if l.startswith("routewise_")][:8]
        for line in lines:
            print(line)

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
