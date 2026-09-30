# LLM eval harness + zero-touch deploy rollback

Two patterns extracted and genericized from **TenantDesk**, a production
SaaS I built (an AI-powered tenant-maintenance bot for rental agencies —
live at tenantdesk.io). Both are re-usable engineering patterns, not
product code: domain-specific prompts, the multi-tenant isolation
architecture, and the last several months of feature work stay private,
since that's the part that's actually the product.

- [`eval_harness/`](eval_harness/) — testing and scoring an LLM-driven
  pipeline deterministically: a prompt-keyed stand-in for the model, a
  structured-output wrapper with bounded retries, a disposable database
  per test, and a golden-case eval suite that reports accuracy rather than
  a single pass/fail.
- [`deploy-rollback/`](deploy-rollback/) — a deploy script that tags the
  running image before every deploy and automatically rolls back on either
  a failed build or a failed post-deploy health check, so a bad deploy
  self-heals without anyone paging in at 2am.

Each folder has its own README with more detail and instructions to run it.

## Provenance

Both pieces started as real code in a working codebase, then had the
business-specific parts removed or swapped for synthetic equivalents:

| Extracted here | Left private |
|---|---|
| Deterministic model stand-in, structured-output retry wrapper, disposable-DB test fixture, golden-case eval runner | Tuned intake prompts, multi-tenant / per-agency isolation architecture, recent feature work |
| Deploy script's build → tag → rollback control flow | Real hostnames, container names, server details |

<!-- TODO before publishing: add a link to the live product and/or case study here. -->
