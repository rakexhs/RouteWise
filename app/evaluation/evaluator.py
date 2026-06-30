import asyncio
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.evaluation.judge import judge_response
from app.evaluation.prompt_suite import load_prompt_suite


async def _call_gateway(
    client: httpx.AsyncClient,
    prompt: str,
    model: str,
    api_key: str,
    feature: str,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "metadata": {"feature": feature},
    }
    for attempt in range(8):
        resp = await client.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            json=payload,
            headers={"X-API-Key": api_key},
            timeout=60.0,
        )
        if resp.status_code == 429:
            await asyncio.sleep(2.0 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}


async def run_evaluation(limit: int | None = None) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    cases = load_prompt_suite()
    if limit:
        cases = cases[:limit]

    modes = {
        "direct_expensive": "mock-large",
        "auto_route": "auto",
        "cache_warm": "auto",
    }

    results: dict[str, list[dict[str, Any]]] = {k: [] for k in modes}

    async with httpx.AsyncClient() as client:
        for case in cases:
            for mode_name, model in modes.items():
                if mode_name == "cache_warm":
                    await _call_gateway(
                        client, case.prompt, model, settings.demo_api_key, f"eval_{mode_name}"
                    )
                    await asyncio.sleep(1.05)
                start = time.perf_counter()
                data = await _call_gateway(
                    client, case.prompt, model, settings.demo_api_key, f"eval_{mode_name}"
                )
                await asyncio.sleep(1.05)
                elapsed = (time.perf_counter() - start) * 1000
                content = data["choices"][0]["message"]["content"]
                judged = judge_response(case, content)
                results[mode_name].append(
                    {
                        "id": case.id,
                        "category": case.category,
                        "latency_ms": data.get("latency_ms", elapsed),
                        "estimated_cost": data.get("estimated_cost", 0),
                        "cache_status": data.get("cache_status"),
                        "route_reason": data.get("route_reason"),
                        "model": data.get("model"),
                        "quality_score": judged.score,
                        "fallback": "fallback" in data.get("route_reason", ""),
                    }
                )

    summary: dict[str, Any] = {}
    for mode_name, rows in results.items():
        latencies = [r["latency_ms"] for r in rows]
        costs = [r["estimated_cost"] for r in rows]
        qualities = [r["quality_score"] for r in rows]
        cache_hits = sum(1 for r in rows if r["cache_status"] in ("exact_hit", "semantic_hit"))
        fallbacks = sum(1 for r in rows if r["fallback"])
        total_cost = sum(costs)
        summary[mode_name] = {
            "requests": len(rows),
            "cost_per_1000": round((total_cost / max(1, len(rows))) * 1000, 4),
            "p50_latency_ms": round(statistics.median(latencies), 2),
            "p95_latency_ms": round(
                sorted(latencies)[int(0.95 * len(latencies)) - 1] if latencies else 0, 2
            ),
            "cache_hit_rate": round(cache_hits / max(1, len(rows)), 3),
            "fallback_rate": round(fallbacks / max(1, len(rows)), 3),
            "avg_quality_score": round(statistics.mean(qualities), 3),
        }

    report_path = Path("reports/evaluation_results.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RouteWise Evaluation Results",
        "",
        f"Prompts evaluated: {len(cases)}",
        "",
        "| Mode | Cost/1K | p50 ms | p95 ms | Cache Hit % | Fallback % | Quality |",
        "|------|---------|--------|--------|-------------|------------|---------|",
    ]
    for mode_name, s in summary.items():
        lines.append(
            f"| {mode_name} | ${s['cost_per_1000']:.4f} | {s['p50_latency_ms']} | "
            f"{s['p95_latency_ms']} | {s['cache_hit_rate']*100:.1f}% | "
            f"{s['fallback_rate']*100:.1f}% | {s['avg_quality_score']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Quality/Cost Tradeoff",
            "",
            "- **direct_expensive**: highest quality baseline, highest cost.",
            "- **auto_route**: routes simple prompts to cheaper models.",
            "- **cache_warm**: repeats prompts to measure cache savings.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines))
    return summary, str(report_path)
