# Watt — Product Requirements and Roadmap

Status: local demo verified in a fresh checkout. [Design](design.md) owns technical decisions; [progress](../PROGRESS.md) records the verification, screenshots, and walkthrough.

## Product brief

**Watt helps retail electricity analysts explain why portfolio margins changed and decide what to investigate next.** A workbook refresh can produce updated numbers; the analyst still has to break down changes, compare customer groups, check contracts and cost records, and prepare findings another team can verify.

The primary user is a retail energy finance or commercial analyst. Pricing and supply teams consume the resulting findings. The recurring job is: after a reporting refresh, identify material margin changes, determine what the evidence supports, and isolate questions that need a person. Retention is one decision the analysis can inform.

## Required local demo

| Requirement | Acceptance |
| --- | --- |
| Portfolio review | Refresh to a seeded reporting snapshot and reconcile the portfolio change across Solar, High Winter Usage, and Low Winter Usage. The analyst can drill into a contract and its monthly margins. |
| Live investigation | Launch from a flagged change and show actual progress. The agent queries approved analytical tools and retrieves applicable passages from a prepared source library. |
| Evidence and uncertainty | Each material finding links to source records or calculations. Watt distinguishes a documented adjustment, recurring plan pressure, and an unexplained usage change. An open question does not block unrelated findings. |
| Analyst intervention | Supply evidence for one unresolved event. Watt keeps provenance and revises only the conclusions that depend on it. |
| Decision support | Compare a retention offer against no offer using editable assumptions. Show incremental contribution and break-even conditions without claiming to predict offer effectiveness. |
| Reproducibility | A fresh checkout can run the demo using documented setup and a clearly labeled synthetic portfolio. Saved findings persist and authentication or runtime failures are visible. |

The demo succeeds when a reviewer can reproduce the margin bridge, verify a cited explanation, identify an unresolved cause, and change a scenario assumption to see its effect. Verification includes deterministic financial tests, retrieval and agent evals, and a browser test of the complete flow. Local delivery is required; public hosting and quantified customer savings are not demo acceptance criteria.

## Implementation roadmap

| Milestone | Exit criterion |
| --- | --- |
| 0. SDK feasibility | Confirm a real subscription-authenticated turn, narrow custom tool access, streamed tool progress, structured findings, and enforceable restrictions before choosing the runtime configuration. |
| 1. Financial foundation | Seed immutable reporting snapshots; verify exact contract-month, group, and portfolio totals. Add version-aware document retrieval and golden fixtures. |
| 2. Portfolio experience | Build the dashboard and drill-down to contracts and months, including data freshness, empty states, and reconciliation. |
| 3. Investigation | Add the bounded investigator, persisted progress, evidence inspection, and explicit unresolved items. Test successful and partial runs. |
| 4. Decision support | Add analyst-supplied evidence, revision history, follow-up questions, and the retention comparison. |
| 5. Delivery | Run the test and eval suites, rehearse a fresh local setup, and record the working demo. |

Use the stack in the design. [Admire The Web](https://admiretheweb.com/) is an optional visual reference for layout and interaction; keep the implementation on the planned component stack. Prioritize readable tables, well-labeled charts, and quick access to evidence over decorative polish.

## Beyond the demo

- **Validate the workflow:** Ask retail energy analysts to review a realistic investigation. Measure time to a defensible finding, reconciliation accuracy, unsupported claims, and whether escalations reach the right person. Compare against their current workflow before claiming savings.
- **Pilot with approved data:** Add read-only database integration and a team-specific margin definition. Define access, data retention, audit, and hosting requirements before using real customer records.
- **Expand where evidence supports it:** Add scheduled reviews, pricing and supply handoffs, richer scenarios, and maintained external sources. Add semantic retrieval if evals show material keyword-search misses. Retention uplift prediction would require intervention evidence; supply-position analysis would require forecasts and actual positions. Neither is part of the demo.
