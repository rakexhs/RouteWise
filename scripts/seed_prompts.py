#!/usr/bin/env python3
"""Seed and verify the evaluation prompt suite."""

import json
from pathlib import Path

PROMPTS = [
    ("summarization", "Summarize the benefits of microservices in three bullet points.", ["microservices", "scalable"]),
    ("classification", "Classify sentiment: 'Great product, terrible support.'", ["mixed", "negative"]),
    ("coding_explanation", "Explain what a linked list is.", ["node", "pointer", "list"]),
    ("support_question", "How do I change my billing email?", ["billing", "email", "settings"]),
    ("factual_answer", "What is photosynthesis?", ["light", "energy", "plants"]),
]


def main() -> None:
    path = Path("data/prompt_suite.jsonl")
    if path.exists():
        count = sum(1 for line in path.read_text().splitlines() if line.strip())
        print(f"Prompt suite exists with {count} prompts")
        if count >= 30:
            return

    existing = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                existing.append(json.loads(line))

    start = len(existing) + 1
    for i, (category, prompt, keywords) in enumerate(PROMPTS, start=start):
        existing.append(
            {
                "id": f"seed-{i:02d}",
                "category": category,
                "prompt": prompt,
                "expected_keywords": keywords,
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for item in existing:
            f.write(json.dumps(item) + "\n")
    print(f"Wrote {len(existing)} prompts to {path}")


if __name__ == "__main__":
    main()
