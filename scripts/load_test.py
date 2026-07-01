#!/usr/bin/env python3
"""Load test for the RouteWise gateway.

Runs a short warmup, then sustains a fixed number of concurrent workers for a
set duration and reports throughput plus latency percentiles. Uses unique
prompts so results reflect the uncached routing path rather than cache hits.

Run the gateway with the rate limit raised so the limiter isn't what gets
measured:

    RATE_LIMIT_PER_MINUTE=1000000 make run
    python scripts/load_test.py --concurrency 10 --duration 60
"""

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings

BASE = "http://127.0.0.1:8000"


async def one_request(client: httpx.AsyncClient, api_key: str, i: int) -> float:
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"Load test probe {i}: summarize topic {i * 13} in one line."}],
        "metadata": {"feature": "load_test"},
    }
    start = time.perf_counter()
    resp = await client.post(
        f"{BASE}/v1/chat/completions",
        json=payload,
        headers={"X-API-Key": api_key},
        timeout=30.0,
    )
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def worker(
    client: httpx.AsyncClient,
    api_key: str,
    worker_id: int,
    stop_at: float,
    latencies: list[float],
    errors: list[str],
) -> None:
    i = 0
    while time.perf_counter() < stop_at:
        try:
            latencies.append(await one_request(client, api_key, worker_id * 1_000_000 + i))
        except Exception as exc:
            errors.append(type(exc).__name__)
        i += 1


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--duration", type=int, default=60, help="seconds")
    parser.add_argument("--warmup", type=int, default=20, help="warmup requests")
    args = parser.parse_args()

    settings = get_settings()
    limits = httpx.Limits(max_connections=args.concurrency)

    async with httpx.AsyncClient(limits=limits) as client:
        # Warmup primes the database, tokenizer, and connection handling so
        # cold-start cost doesn't skew the percentiles.
        for i in range(args.warmup):
            try:
                await one_request(client, settings.demo_api_key, 900_000_000 + i)
            except Exception:
                pass

        latencies: list[float] = []
        errors: list[str] = []
        stop_at = time.perf_counter() + args.duration
        start = time.perf_counter()
        await asyncio.gather(
            *[
                worker(client, settings.demo_api_key, w, stop_at, latencies, errors)
                for w in range(args.concurrency)
            ]
        )
        wall = time.perf_counter() - start

    if not latencies:
        print(f"All requests failed: {errors[:5]}")
        sys.exit(1)

    s = sorted(latencies)
    p50 = statistics.median(s)
    p95 = s[max(0, int(0.95 * len(s)) - 1)]
    p99 = s[max(0, int(0.99 * len(s)) - 1)]
    throughput = len(latencies) / wall

    report = Path("reports/benchmark_results.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# RouteWise Benchmark Results

Sustained load test against the gateway with mock providers, measuring gateway
overhead: routing, cache lookup, rate-limit checks, PII scan, and persistence.
The gateway ran with the rate limit raised so the limiter itself isn't what
gets benchmarked, and a {args.warmup}-request warmup is excluded from the
numbers. Prompts are unique, so every request takes the uncached routing path.

| Metric | Value |
|--------|-------|
| Duration (s) | {wall:.0f} |
| Concurrent workers | {args.concurrency} |
| Completed requests | {len(latencies)} |
| Errors | {len(errors)} |
| Throughput (req/s) | {throughput:.1f} |
| p50 latency (ms) | {p50:.0f} |
| p95 latency (ms) | {p95:.0f} |
| p99 latency (ms) | {p99:.0f} |

Reproduce with:

```bash
RATE_LIMIT_PER_MINUTE=1000000 make run
python scripts/load_test.py --concurrency {args.concurrency} --duration {args.duration}
```
"""
    report.write_text(content)
    print(content)
    print(f"Report written to {report}")


if __name__ == "__main__":
    asyncio.run(main())
