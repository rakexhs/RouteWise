import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PromptCase:
    id: str
    category: str
    prompt: str
    expected_keywords: list[str]


def load_prompt_suite(path: str | Path = "data/prompt_suite.jsonl") -> list[PromptCase]:
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            cases.append(
                PromptCase(
                    id=data["id"],
                    category=data["category"],
                    prompt=data["prompt"],
                    expected_keywords=data.get("expected_keywords", []),
                )
            )
    return cases
