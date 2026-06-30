from dataclasses import dataclass

from app.evaluation.prompt_suite import PromptCase


@dataclass
class JudgeResult:
    score: float
    passed_keywords: list[str]
    missing_keywords: list[str]
    notes: str


def judge_response(case: PromptCase, response_text: str) -> JudgeResult:
    text_lower = response_text.lower()
    passed = []
    missing = []
    for kw in case.expected_keywords:
        if kw.lower() in text_lower:
            passed.append(kw)
        else:
            missing.append(kw)

    keyword_score = len(passed) / max(1, len(case.expected_keywords))
    length_bonus = 0.1 if len(response_text.split()) >= 10 else 0.0
    structure_bonus = 0.1 if any(c in response_text for c in ".:;\n") else 0.0
    score = min(1.0, keyword_score * 0.8 + length_bonus + structure_bonus)

    notes = f"category={case.category} keywords={len(passed)}/{len(case.expected_keywords)}"
    return JudgeResult(
        score=round(score, 3),
        passed_keywords=passed,
        missing_keywords=missing,
        notes=notes,
    )
