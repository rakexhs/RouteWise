import re
from dataclasses import dataclass

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


@dataclass
class PIIDetection:
    has_pii: bool
    types: list[str]


def detect_pii(text: str) -> PIIDetection:
    types = []
    if EMAIL_PATTERN.search(text):
        types.append("email")
    if PHONE_PATTERN.search(text):
        types.append("phone")
    if SSN_PATTERN.search(text):
        types.append("ssn")
    if CARD_PATTERN.search(text):
        types.append("credit_card")
    return PIIDetection(has_pii=bool(types), types=types)


def redact_pii(text: str) -> str:
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = CARD_PATTERN.sub("[REDACTED_CARD]", text)
    return text


def redact_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"role": m["role"], "content": redact_pii(m["content"])} for m in messages]
