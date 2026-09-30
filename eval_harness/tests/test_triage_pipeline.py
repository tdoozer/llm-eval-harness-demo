from __future__ import annotations

import pytest

from app.db import count_tickets, insert_ticket
from app.llm_client import RetryLog, StructuredResponseError, get_structured_response
from app.triage import TriageValidationError, extract_ticket_fields


def test_extracts_urgent_plumbing_ticket(fake_llm):
    fields = extract_ticket_fields(fake_llm, "There's a burst pipe flooding the kitchen right now.")
    assert fields.category == "plumbing"
    assert fields.urgency == "high"


def test_extracts_low_urgency_electrical_ticket(fake_llm):
    fields = extract_ticket_fields(fake_llm, "Just a flickering light in the hallway, no rush.")
    assert fields.category == "electrical"
    assert fields.urgency == "medium"


def test_unclassifiable_ticket_falls_back_to_other(fake_llm):
    fields = extract_ticket_fields(fake_llm, "What time does the building gym close?")
    assert fields.category == "other"


def test_structured_response_retries_on_malformed_first_attempt(flaky_llm):
    """The first call returns non-JSON; the wrapper must retry rather than surface garbage."""
    log = RetryLog()
    result = get_structured_response(
        flaky_llm,
        "irrelevant prompt mentioning a burst pipe",
        required_keys={"category", "urgency", "summary"},
        log=log,
    )
    assert result["category"] == "plumbing"
    assert log.attempts == 2  # first attempt failed, second succeeded


def test_structured_response_raises_after_exhausting_retries():
    class AlwaysBrokenLLM:
        def complete(self, prompt: str) -> str:
            return "still not json"

    with pytest.raises(StructuredResponseError):
        get_structured_response(
            AlwaysBrokenLLM(), "prompt", required_keys={"category"}, max_retries=1
        )


def test_hallucinated_category_is_rejected():
    class HallucinatingLLM:
        def complete(self, prompt: str) -> str:
            return '{"category": "haunted", "urgency": "high", "summary": "ghosts"}'

    with pytest.raises(TriageValidationError):
        extract_ticket_fields(HallucinatingLLM(), "something spooky")


def test_db_starts_empty(db):
    assert count_tickets(db) == 0


def test_db_is_isolated_between_tests(db, fake_llm):
    """Runs after test_db_starts_empty; if state leaked, count would be > 0 here too."""
    fields = extract_ticket_fields(fake_llm, "locked out, key broke off in the door")
    insert_ticket(db, "locked out, key broke off in the door", fields.category, fields.urgency, fields.summary)
    assert count_tickets(db) == 1
