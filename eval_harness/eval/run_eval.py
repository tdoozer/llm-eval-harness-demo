#!/usr/bin/env python3
"""Run the golden-case eval suite and print a scoring report.

Usage:
    python -m eval.run_eval [--threshold 1.0] [--json report.json]

Exits non-zero if accuracy falls below --threshold, so this can gate CI the
same way a regular test suite does — the difference is that it scores
*behavior against expected structured output* rather than asserting a
single pass/fail per test.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.fake_llm import FakeLLM  # noqa: E402
from app.llm_client import StructuredResponseError  # noqa: E402
from app.triage import TriageValidationError, extract_ticket_fields  # noqa: E402

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "golden_cases.json"


@dataclass
class CaseResult:
    id: str
    passed: bool
    expected_category: str
    actual_category: str | None
    expected_urgency: str
    actual_urgency: str | None
    error: str | None = None


def run(threshold: float) -> tuple[list[CaseResult], float]:
    cases = json.loads(_FIXTURES.read_text(encoding="utf-8"))
    llm = FakeLLM()
    results: list[CaseResult] = []

    for case in cases:
        try:
            fields = extract_ticket_fields(llm, case["message"])
        except (StructuredResponseError, TriageValidationError) as exc:
            results.append(
                CaseResult(
                    id=case["id"],
                    passed=False,
                    expected_category=case["expected_category"],
                    actual_category=None,
                    expected_urgency=case["expected_urgency"],
                    actual_urgency=None,
                    error=str(exc),
                )
            )
            continue

        passed = (
            fields.category == case["expected_category"]
            and fields.urgency == case["expected_urgency"]
        )
        results.append(
            CaseResult(
                id=case["id"],
                passed=passed,
                expected_category=case["expected_category"],
                actual_category=fields.category,
                expected_urgency=case["expected_urgency"],
                actual_urgency=fields.urgency,
            )
        )

    accuracy = sum(r.passed for r in results) / len(results) if results else 0.0
    return results, accuracy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=1.0)
    parser.add_argument("--json", type=Path, default=None, help="write the report as JSON to this path")
    args = parser.parse_args()

    results, accuracy = run(args.threshold)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.id}")
        if not r.passed:
            if r.error:
                print(f"       error: {r.error}")
            else:
                print(f"       category: expected={r.expected_category!r} actual={r.actual_category!r}")
                print(f"       urgency:  expected={r.expected_urgency!r} actual={r.actual_urgency!r}")

    print(f"\naccuracy: {accuracy:.1%} ({sum(r.passed for r in results)}/{len(results)})")

    if args.json:
        args.json.write_text(
            json.dumps({"accuracy": accuracy, "results": [asdict(r) for r in results]}, indent=2),
            encoding="utf-8",
        )

    return 0 if accuracy >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
