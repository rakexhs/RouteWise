# RouteWise Evaluation Results

Prompts evaluated: 32

| Mode | Cost/1K | p50 ms | p95 ms | Cache Hit % | Fallback % | Quality |
|------|---------|--------|--------|-------------|------------|---------|
| direct_expensive | $0.0128 | 248.85 | 616.72 | 46.9% | 0.0% | 0.396 |
| auto_route | $0.0128 | 55.02 | 73.56 | 100.0% | 0.0% | 0.396 |
| cache_warm | $0.0128 | 29.07 | 55.92 | 100.0% | 0.0% | 0.396 |

## Quality/Cost Tradeoff

- **direct_expensive**: highest quality baseline, highest cost.
- **auto_route**: routes simple prompts to cheaper models.
- **cache_warm**: repeats prompts to measure cache savings.
