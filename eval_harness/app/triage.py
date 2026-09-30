"""Synthetic domain: incoming support-ticket triage.

Mirrors the shape of a real intake pipeline (free-text message in,
validated structured fields out) without any of the business-specific
prompt tuning that would make it a copy of a real product's prompts.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.llm_client import LLMClient, get_structured_response

ALLOWED_CATEGORIES = {"plumbing", "electrical", "appliance", "access", "other"}
ALLOWED_URGENCY = {"low", "medium", "high"}

_PROMPT_TEMPLATE = """Classify the following support ticket.
Return a JSON object with exactly these keys:
- category: one of {categories}
- urgency: one of {urgency}
- summary: a short one-sentence summary

Ticket:
\"\"\"{message}\"\"\"
"""


class TriageValidationError(ValueError):
    """Raised when the model returned well-formed JSON with out-of-range values."""


@dataclass(frozen=True)
class TicketFields:
    category: str
    urgency: str
    summary: str


def build_prompt(message: str) -> str:
    return _PROMPT_TEMPLATE.format(
        categories=sorted(ALLOWED_CATEGORIES),
        urgency=sorted(ALLOWED_URGENCY),
        message=message,
    )


def extract_ticket_fields(llm: LLMClient, message: str) -> TicketFields:
    """Run the full pipeline: prompt -> structured response -> validated dataclass.

    Raises StructuredResponseError if the model never returns parseable JSON
    with the required keys, or TriageValidationError if it does but the
    values are outside the allowed sets (e.g. a hallucinated category).
    """
    prompt = build_prompt(message)
    data = get_structured_response(
        llm, prompt, required_keys={"category", "urgency", "summary"}
    )

    if data["category"] not in ALLOWED_CATEGORIES:
        raise TriageValidationError(f"unknown category: {data['category']!r}")
    if data["urgency"] not in ALLOWED_URGENCY:
        raise TriageValidationError(f"unknown urgency: {data['urgency']!r}")

    return TicketFields(
        category=data["category"],
        urgency=data["urgency"],
        summary=str(data["summary"]),
    )
