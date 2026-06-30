#!/usr/bin/env python3
"""Simple load test for RouteWise gateway."""

import asyncio
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings

BASE = "http://127.0.0.1:8000"
CONCURRENCY = 50
REQUESTS = 50


async def one_request(client: httpx.AsyncClient, api_key: str, i: int) -> float:
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"Load test request {i % 10}"}],
        "metadata": {"feature": "load_test"},
    }
    start = time.perf_counter()
    resp = await client.post(
        f"{BASE}/v1/chat/completions",
        json=payload,
        headers={"X-API-Key": api_key},
        timeout=60.0,
    )
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    settings = get_settings()
    latencies: list[float] = []
    errors = 0

    async with httpx.AsyncClient() as client:
        tasks = [one_request(client, settings.demo_api_key, i) for i in range(REQUESTS)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                errors += 1
            else:
                latencies.append(r)

    p50 = statistics.median(latencies) if latencies else 0
    p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1] if latencies else 0

    report = Path("reports/benchmark_results.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# RouteWise Benchmark Results

| Metric | Value |
|--------|-------|
| Concurrent requests | {CONCURRENCY} |
| Total requests | {REQUESTS} |
| Successful | {len(latencies)} |
| Errors | {errors} |
| p50 latency (ms) | {p50:.2f} |
| p95 latency (ms) | {p95:.2f} |
| Throughput (req/s) | {len(latencies) / max(0.001, sum(latencies)/1000 / len(latencies) if latencies else 1):.2f} |
"""
    report.write_text(content)
    print(content)
    print(f"Report written to {report}")


if __name__ == "__main__":
    asyncio.run(main())
