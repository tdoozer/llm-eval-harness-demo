"""LLM client abstractions used by the triage pipeline.

Two things live here on purpose:

1. `LLMClient` — a tiny protocol any backend (a real API client, or a
   deterministic stand-in for tests) can satisfy with one method.
2. `get_structured_response` — a wrapper that turns "the model returned some
   text" into "the model returned a validated dict, or we failed loudly."
   Models don't reliably follow JSON-output instructions on the first try;
   this retries a bounded number of times against fresh completions rather
   than silently returning malformed or partial data to the caller.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return raw model output for a prompt. No parsing, no retries."""
        ...


class StructuredResponseError(RuntimeError):
    """Raised when the model never produced a valid, schema-complete response."""


@dataclass
class RetryLog:
    attempts: int = 0
    raw_responses: list[str] = field(default_factory=list)


def get_structured_response(
    llm: LLMClient,
    prompt: str,
    required_keys: set[str],
    max_retries: int = 2,
    log: RetryLog | None = None,
) -> dict:
    """Call `llm`, parse JSON, validate required keys, retry on failure.

    Raises StructuredResponseError (never returns a partial/invalid dict)
    if every attempt fails.
    """
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        raw = llm.complete(prompt)
        if log is not None:
            log.attempts += 1
            log.raw_responses.append(raw)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if not isinstance(parsed, dict):
            last_error = TypeError(f"expected a JSON object, got {type(parsed).__name__}")
            continue
        missing = required_keys - parsed.keys()
        if missing:
            last_error = KeyError(f"missing required keys: {sorted(missing)}")
            continue
        return parsed

    raise StructuredResponseError(
        f"no valid structured response after {max_retries + 1} attempt(s): {last_error}"
    )
