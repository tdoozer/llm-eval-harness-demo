# LLM eval harness (extracted pattern)

Extracted and genericized from a production pattern I use in **TenantDesk**,
an AI-powered tenant-maintenance bot for rental agencies (live at
tenantdesk.io). The real system triages tenant-reported issues over
Telegram/WhatsApp; this demo triages a synthetic "support ticket" instead,
using fabricated data and a fabricated prompt — the pattern is real, the
domain and the tuned prompts are not.

## What this demonstrates

Testing LLM-driven pipelines deterministically is different from testing
regular code: the thing under test is nondeterministic, slow, and costs
money to call for real. The pattern here:

1. **A deterministic stand-in for the model** ([`app/fake_llm.py`](app/fake_llm.py))
   that inspects the incoming prompt and returns a plausible structured
   response for it — not one fixed canned reply, but prompt-keyed, so it
   supports writing many distinct test/eval cases against it.
2. **A structured-output wrapper with bounded retries** ([`app/llm_client.py`](app/llm_client.py))
   that parses and validates the model's JSON before anything downstream
   ever sees it, retrying against fresh completions rather than passing
   through malformed or partial output. `test_structured_response_retries_on_malformed_first_attempt`
   exercises this directly with a stand-in whose first response is broken.
3. **A disposable database per test** ([`app/db.py`](app/db.py)) — fresh
   schema, empty tables, deleted on teardown. No shared state between
   tests, no network calls, no flakiness. (The real system uses a
   throwaway Postgres via testcontainers; this demo uses SQLite so it runs
   anywhere with zero extra infrastructure — same pattern, lighter engine.)
4. **A golden-case eval suite, separate from the unit tests**
   ([`eval/run_eval.py`](eval/run_eval.py), [`fixtures/golden_cases.json`](fixtures/golden_cases.json)) —
   scores pipeline output against expected structured fields and reports
   per-case pass/fail plus aggregate accuracy, so a regression shows up as
   a number dropping, not just a boolean going red.

## Running it

```bash
pip install -r requirements.txt

# unit tests — fast, deterministic, no network
python -m pytest tests/ -v

# eval report — scores the pipeline against the golden-case fixtures
python -m eval.run_eval
python -m eval.run_eval --json report.json   # write a machine-readable report
```

## What's deliberately left out

The tuned intake prompts, the multi-tenant isolation architecture, and
anything from the last several months of feature work stay in the private
repo — that's the part of TenantDesk that's actually a product, not a
testing pattern. This extract is the pattern, on a throwaway domain.
