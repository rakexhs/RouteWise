# RouteWise Benchmark Results

Sustained load test against the gateway with mock providers, measuring gateway
overhead: routing, cache lookup, rate-limit checks, PII scan, and persistence.
The gateway ran with the rate limit raised so the limiter itself isn't what
gets benchmarked, and a 20-request warmup is excluded from the
numbers. Prompts are unique, so every request takes the uncached routing path.

| Metric | Value |
|--------|-------|
| Duration (s) | 60 |
| Concurrent workers | 10 |
| Completed requests | 14581 |
| Errors | 0 |
| Throughput (req/s) | 242.7 |
| p50 latency (ms) | 55 |
| p95 latency (ms) | 91 |
| p99 latency (ms) | 117 |

Reproduce with:

```bash
RATE_LIMIT_PER_MINUTE=1000000 make run
python scripts/load_test.py --concurrency 10 --duration 60
```
