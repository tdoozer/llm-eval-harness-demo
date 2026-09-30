"""Deterministic stand-in for a real model, keyed on the incoming prompt.

This is the core test-harness trick: instead of mocking "the OpenAI call"
with one fixed return value, the stand-in inspects the prompt's content
(the ticket message embedded in it) and returns a plausible structured
answer for it. That makes it possible to write eval cases the same shape
as production ones — text in, expected structured fields out — with zero
network calls and fully deterministic, sub-millisecond runs.

`FlakyOnceLLM` additionally demonstrates the retry path in
`llm_client.get_structured_response`: its first response is deliberately
malformed, its second is valid.
"""
from __future__ import annotations

import json

_RULES: list[tuple[list[str], dict]] = [
    (["leak", "flood", "burst pipe"], {"category": "plumbing", "urgency": "high"}),
    (["dripping", "slow drain"], {"category": "plumbing", "urgency": "low"}),
    (["no power", "sparking", "exposed wire"], {"category": "electrical", "urgency": "high"}),
    (["flickering light"], {"category": "electrical", "urgency": "medium"}),
    (["fridge", "washing machine", "oven"], {"category": "appliance", "urgency": "medium"}),
    (["locked out", "key broke", "can't get in"], {"category": "access", "urgency": "high"}),
]


class FakeLLM:
    """Keyword-matches the ticket message and returns a canned JSON response."""

    def complete(self, prompt: str) -> str:
        lower = prompt.lower()
        for keywords, fields in _RULES:
            if any(kw in lower for kw in keywords):
                return json.dumps(
                    {
                        "category": fields["category"],
                        "urgency": fields["urgency"],
                        "summary": f"Ticket matched rule for {fields['category']}.",
                    }
                )
        return json.dumps({"category": "other", "urgency": "low", "summary": "Unclassified ticket."})


class FlakyOnceLLM:
    """Returns malformed JSON on the first call, a valid FakeLLM-style response after."""

    def __init__(self) -> None:
        self._calls = 0
        self._delegate = FakeLLM()

    def complete(self, prompt: str) -> str:
        self._calls += 1
        if self._calls == 1:
            return "not json at all"
        return self._delegate.complete(prompt)
