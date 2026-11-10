# Watt — Local Demo Design

## Purpose and scope

Watt helps a retail energy analyst investigate portfolio margin changes, inspect the evidence, and compare a retention offer with no offer. The hackathon deliverables are a working local demo and a reproducible GitHub checkout. Customer and company records are synthetic; prepared public sources are identified separately. Hosting, live web research, trade execution, and automated outreach are outside v1.

The analyst refreshes the portfolio, sees a modest overall decline, and discovers offsetting movements across customer groups. They launch an investigation into the solar group, verify one explanation, supply evidence for one open issue, and compare a retention offer against no offer. Success means they can distinguish recorded facts, calculated contributions, supported explanations, and unresolved causes without reading the raw execution log.

## Portfolio and margin model

- Seed 10,000 fictional Texas retail electricity customers across January 2024–December 2025. Use 200 solar customers (2%) as a demo assumption, not a Texas market estimate. Refresh activates the validated December snapshot after the initial November snapshot; it does not generate random records.
- Use three mutually exclusive primary groups: **Solar**, **High winter usage**, and **Low winter usage**. Documented solar status takes precedence in the top-level rollup. Classify the remaining customers by their winter electricity usage profile. Keep solar status and winter profile as independent attributes so analysts can inspect both winter profiles within Solar. Solar subgroups can also be compared by plan and credit arrangement.
- For the demo, use mean imported kWh per billed day across December 2024–February 2025, requiring complete, valid observations for all three months. Use the median among eligible non-solar customers as the cutoff; values at or above it are high. Freeze profiles across the November and December comparison so the same usage swing being investigated cannot move a customer between groups. Profiles describe observed electricity use; they do not prove whether the customer heats with gas or electricity. Missing solar designation or insufficient profile evidence is a visible data-quality exception rather than a fourth primary group; include its dollars in reconciliation.
- Drill down from **portfolio → customer group → customer contract → monthly contract margins**. The financial grain is one contract per reporting month. Components within a month explain that month; there is no daily margin view. An active contract shows realized margin to date and coverage. A completed contract shows full realized margin only when all relevant months are available. Future months appear only in separately labeled scenarios. Keep the portfolio period filter distinct from the contract-to-date view.
- Monthly reported margin is gross billed energy revenue plus fixed fees, less bill credits, export credits, and itemized wholesale energy, ancillary service, transmission, and other supply costs. Keep grid imports, grid exports, and export credits separate. Use decimal arithmetic and count each cost once. Contract totals sum the recorded monthly amounts; missing months are visible and never treated as zero.
- Use posting month for reported margin and retain service month on adjustments. A separately labeled normalized view reconciles the effect of identified prior-period adjustments without rewriting the previous month. Break down comparable costs into usage and effective unit-cost effects; use direct line-item differences for zero-usage or adjustment-only records. Allocated historical costs do not establish avoidable future costs or hedge exposure.

The seeded November-to-December comparison targets a $1,000 portfolio decline: high winter usage improves $2,200, low winter usage declines $800, and solar declines $2,400. Within Solar, fixtures account for a $900 prior-period settlement adjustment, $1,200 of recurring plan-related pressure supported by several months of records, and $300 associated with recorded usage changes whose cause is initially unresolved. The fixture has no unclassified contribution in this comparison; separate test cases cover exceptions. Show contribution dollars alongside group size and per-customer margin so a small cohort can be compared fairly.

## Architecture and analyst workflow

- **Stack:** Next.js, TypeScript, Tailwind, shadcn/ui and Recharts; Python, FastAPI and Pydantic; PostgreSQL in Docker; Codex Python SDK signed in with ChatGPT; pytest and Playwright. First verify SDK authentication, structured output, progress events, custom tool access, and the ability to restrict unwanted tools. If this gate fails, record the result and revisit the runtime design without silently changing billing or permissions.
- **Data access:** Use read-only analytical views and a separate application-state write role. SQL and defined Python functions own financial arithmetic. Narrow tools cover margin bridges, group comparisons, contract timelines, source retrieval, weather lookups, and scenario calculations. The agent cannot run arbitrary SQL or unrestricted shell commands, change source data, or execute business decisions.
- **Retrieval:** Use exact IDs for known contracts and adjustment records; use PostgreSQL full-text search with type, date, version, and applicability filters for document RAG. Preserve section anchors and source links. Weather is a structured location/date lookup. Exclude sources published after the analysis cutoff from historical attribution. A relevant notice or weather event alone does not prove a cause. Add semantic search through pgvector only if retrieval evals identify material misses that the baseline cannot address.
- **Runs:** FastAPI creates an investigation job bound to a snapshot, period, and group. A single local worker handles one active job at a time. Persist findings and progress events; stream actual tool progress to the browser and reconnect on reload. Limit runs to five minutes and 20 tool calls; report partial results and the limit explicitly. Retain failed, cancelled, and interrupted runs, with reruns recorded as new revisions.
- **Interface:** Show the portfolio bridge and group drilldown. Flag group changes for review at $1,000 and 10% of absolute prior margin, or at a sign change with a $1,000 movement; all groups remain accessible. Click **Investigate** for deeper analysis. Plain-language follow-ups reuse the saved investigation and return validated tables or supported charts. The evidence view shows records, calculations, and document passages. Technical events are separate; no private model reasoning is displayed.
- **Findings and review:** Each finding has a scope, evidence references, status, and any dependent conclusions. Distinguish observed/calculated facts, supported explanations, hypotheses, and unresolved causes. Verify numerical claims, evidence references, dates, and scope before publication. A missing move-out record cannot establish a move. Prioritize open items by financial significance and decision impact; continue independent analysis. An analyst can supply a dated, matching record or leave an item open. Supplied evidence retains its provenance and creates a revision without overwriting source records.

## Retention scenario

Compare a 12-month offer scenario with no offer. Give the analyst editable demo assumptions for customer count, future contribution per customer conditional on staying, baseline and offer stay probabilities, outreach cost per contacted customer, and incentive per customer who stays with the offer.

**Incremental expected contribution = customer count × [(offer stay probability − baseline stay probability) × future contribution − outreach cost − offer stay probability × incentive].**

Show break-even uplift when feasible and how the result changes under different assumptions. The scenario omits partial-year departure timing and does not predict offer effectiveness. Use explicit future contribution assumptions rather than treating allocated historical margin as avoidable. Carry unresolved findings into scenario caveats only where relevant.

## Verification and definition of done

| Layer | Required verification |
| --- | --- |
| Deterministic tests | Group assignment and no double-counting; historical cutoff; monthly-to-contract and group-to-portfolio reconciliation; credit and adjustment arithmetic; missing months; scenario edge cases. |
| Retrieval evals | Correct clause, adjustment record, or external passage appears in returned evidence; stale versions, future publications, and wrong contracts are excluded. |
| Agent evals | The agent finds supported drivers, cites relevant evidence, distinguishes temporal coincidence from causation, leaves unsupported move-outs unresolved, and continues unrelated work. |
| Browser tests | Refresh, drill down, investigate, inspect evidence, submit a resolution, and compare a scenario. Also verify failure and partial-result states. |

Start with roughly 20 small retrieval and agent cases combined, including variations beyond the main demo. Run code-based graders for exact values, evidence IDs, statuses, and forbidden claims where feasible. Use a written rubric and human inspection for whether evidence supports the wording and whether the follow-up is useful. A reviewer subagent can flag subtle reasoning issues; its judgment does not replace executable checks or human review. Repeat critical live cases before recording and retain results for comparison.

After approval, sequence the work: SDK feasibility, deterministic fixtures and calculations, portfolio UI, investigation and evidence, analyst review and scenarios, then end-to-end checks and rehearsal. Aim for a warm portfolio response within two seconds and a typical investigation within 90 seconds; measure both locally rather than treating model latency as a correctness guarantee.

Done means a fresh checkout can be configured, seeded, authenticated, and run using the README; the complete demo uses real queries and investigations, persists results across restarts, and ships without credentials. Stretch goals include richer scenarios, team-specific exports, scheduled investigations, semantic retrieval if warranted, and hosted deployment.

## Decision log

- **2026-11-09:** Replaced the generic non-solar group with high and low winter usage profiles, retaining solar and winter profile as independent attributes. Reduced the synthetic solar share from 20% to 2% and rebalanced the demo fixture.
- **2026-11-09:** Established the contract-month as the financial grain and separated realized contract totals from future scenarios.
- **2026-11-09:** Kept PostgreSQL document retrieval as the baseline; made retrieval and agent evals explicit, with semantic retrieval contingent on measured gaps.
- **2026-11-09:** Implemented the first financial layer in standard-library Python with integer USD cents (exact decimal fixed point). The generated fixture is compressed JSON Lines with explicit snapshot cutoffs. PostgreSQL ingestion remains a separate milestone and should reconcile to these reference totals.
- **2026-11-10:** PostgreSQL loads the shared source rows once. Reporting views require a snapshot filter to select the applicable posting cutoff. The analyst group can read those views but cannot access source relations or write to the reporting schema. SQL calculates its own rollups and is verified against the Python reference.
