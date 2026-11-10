# Watt Progress

## Current state — 2026-11-10

The local Codex SDK feasibility probe passed. The [product brief and roadmap](docs/prd.md) describe demo acceptance and future work; the [design](docs/design.md) owns technical decisions. [AGENTS.md](AGENTS.md) records durable working rules.

The Python margin foundation, PostgreSQL snapshots, and portfolio workspace are verified. The investigator is the next milestone. The SDK probe ran in a temporary Python environment using only a synthetic fixture.

## SDK feasibility evidence — 2026-11-09

- Tested `openai-codex==0.167.0` and its matching bundled CLI on Python 3.13.1. Forced ChatGPT sign-in, unset `OPENAI_API_KEY` and `CODEX_API_KEY`, and confirmed that the SDK reported account type `chatgpt` before a live model turn.
- Received tool-start and tool-completion events for an actual call to a local MCP fixture. The completed turn returned the fixture's exact evidence ID and signed integer margin delta in schema-constrained JSON.
- Used a read-only sandbox and deny-all approvals. The unannotated fixture tool was rejected; declaring the genuinely read-only tool with MCP's `readOnlyHint` allowed it without changing the approval policy. Treat annotations as metadata and enforce read-only access in the tool implementation.
- Disabled shell and unified execution in the probe configuration. A separate turn requesting a harmless shell command completed without any shell or alternate tool event. This is a targeted capability check, not a full audit of the eventual Watt worker and its tool allowlist.

## Margin foundation — 2026-11-09

- Generated 10,000 fictional contracts and 240,000 contract-month records. The [README](README.md) documents how to regenerate the compressed files and run the suite without dependencies.
- Implemented exact cent arithmetic, reported and normalized views, realized contract totals with coverage, and monthly group and portfolio rollups. Winter profiles use only the fixed reference window; missing classifications stay visible in reconciliation.
- All eight tests passed with `python3 -m unittest discover -s tests -v`. A separate read of the exported files verified record counts, unique keys, and the planted solar drivers. November margin was $571,322.95 and December was $570,322.95. High Winter Usage moved +$2,200, Low Winter Usage −$800, and Solar −$2,400.

## PostgreSQL snapshots — 2026-11-10

- Loaded 10,000 synthetic contracts, 240,000 contract-month rows, and 20 adjustments into local PostgreSQL 17.11. The transactional loader refuses an existing installation rather than replacing it. The [README](README.md#load-and-verify-postgresql) documents setup, loading, and verification.
- Ran `python3 -m watt.verify_postgres` as the read-only reporting role. The initial snapshot ended in November (230,000 rows); the refreshed snapshot included December (240,000 rows). Every contract-month, contract total and coverage count, group-month total, and portfolio-month total matched Python for reported and normalized margins.
- A separate read-only subagent confirmed the snapshot cutoffs, December-only adjustments, exact November and December group totals, and no write or private-schema access for `watt_analyst`. The eight Python unit tests also passed.
- Computing the fixed winter median once per query reduced the measured December portfolio rollup from about 20 seconds to 103 ms on this local run. This is a query measurement, not an application latency benchmark.

## Prepared evidence retrieval — 2026-11-10

- Seeded a synthetic library with dated plan revisions, a December settlement note, and a contract-specific service record. Parameterized search applies the snapshot publication cutoff and selected month’s effective dates, selects the latest applicable revision, then filters and ranks matching text.
- Eight live retrieval cases passed, including later publication, stale revision, wrong contract, and unresolved usage. Full PostgreSQL reconciliation and all eight Python unit tests also passed. An independent read-only subagent reran the retrieval cases and confirmed the analyst grants.

## Portfolio experience — 2026-11-10

- Added a FastAPI reporting API and Next.js workspace for snapshot refresh, reported and normalized views, monthly trend, group reconciliation, and contract-month components. The service uses a dedicated reporting-only login with read-only transactions.
- All four Playwright checks, TypeScript, production build, and eight Python tests passed. Browser captures: [portfolio](docs/evidence/portfolio.png) and [contract](docs/evidence/contract.png).
- A read-only subagent independently checked the live handlers against Python, December exclusion, contract coverage and adjustments, and the actual reader role. It also inspected the captured portfolio.

## Next milestone

Implement the persisted investigator, scoped tools, evidence validation, live progress, and unresolved findings. Verify the worker's tool allowlist before connecting Codex to the synthetic data.

## Updating this log

Record the active milestone, concrete verification results, blockers, and the next step. Put product and architecture tradeoffs in the design's decision log and link them here when they affect progress.
