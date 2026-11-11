# Watt Product Requirements Document

| Field | Detail |
| --- | --- |
| Product | Watt, a month-end margin investigation workspace for retail electricity providers |
| Primary user | Retail energy finance or commercial analyst responsible for explaining margin movements |
| Release status | Local hackathon demo implemented and verified with synthetic customer data. Pilot scope and targets are proposed. |
| Decision requested | Validate the month-end workflow with analysts and select a finance sponsor before requesting access to company data. |
| Companion documents | [Technical design and decision log](design.md) · [Implementation and verification history](../PROGRESS.md) · [Local setup](../README.md) |

## 1. Problem and opportunity

At month-end, an analyst can refresh a workbook to see that margin moved. Explaining the movement takes a separate round of work. The analyst compares periods, breaks the movement down by customer group and cost component, checks when charges posted, reads contract and settlement records, and writes an explanation that pricing or supply can verify. A small net change can hide large movements in opposing directions. A late charge can also make current economics look worse than they are.

Watt automates the evidence gathering and reconciliation between **seeing a change** and **having an explanation someone else can check**. The analyst reviews the report, resolves open items when they have evidence, and decides what to do next. A successful output gives a reviewer the amount, the period, the evidence, and any question that still needs an owner.

The initial problem statement comes from the project brief. Its frequency, manual effort, and impact on downstream decisions still need validation in a real close. The synthetic demo establishes that the workflow is feasible.

## 2. Users and jobs

| Role | Job to be done | Product need |
| --- | --- | --- |
| Finance or commercial analyst | Explain a material margin change after the monthly data refresh. | A reconciled breakdown, a quick path to source evidence, and a clear way to record what remains open. |
| Finance lead or controller | Review the explanation before relying on it in reporting. | Clear reporting period and basis, traceable figures, and preserved revisions. This role would own pilot acceptance. |
| Pricing and supply partners | Decide whether a finding warrants a pricing, billing, or operational follow-up. | A concise explanation with the affected group, amount, evidence, and unresolved issue. Dedicated handoffs are a pilot candidate. |

**Primary job story.** When my monthly portfolio numbers refresh, I want to understand which customer groups and cost components moved margin, so I can brief the team with evidence and focus follow-up where judgment is needed.

## 3. Product goals and release scope

| Priority | Local demo scope | Value to the analyst |
| --- | --- | --- |
| P0 | Compare reporting months, reconcile the portfolio to customer groups, and drill into contracts and monthly components. | Find where the movement came from and reproduce the dollars. |
| P0 | Run a scoped investigation, watch its progress, and open an evidence-backed report with explicit gaps. | Spend less time pulling records and checking the same sources by hand. |
| P1 | Attach evidence to an unresolved contract and revisit the original report. | Preserve the close record as new facts arrive. |
| P1 | Ask a follow-up about saved findings and compare a retention offer using editable assumptions. | Continue the analysis in the same workspace. |
| Deferred | Company integrations, shared workspaces, scheduled investigations, export and handoff workflows, expanded cause coverage, and production hosting. | Sequence investments after validating the core workflow. |

The release stops at analysis and analyst review. Posting accounting entries, changing rates, contacting customers, executing trades, and predicting retention uplift are outside scope. Retention modeling supports a hypothetical decision and has lower priority than the margin investigation.

## 4. End-to-end experience

1. **Establish the period.** The analyst opens a data snapshot and selects a reporting month. The portfolio shows its margin, the comparison to the prior month, and movements by group. The analyst can toggle between posted and normalized margin.
2. **Choose what to investigate.** The analyst opens a flagged group or selects any available group. They can inspect the group’s contracts, then inspect one contract’s months and the components within a selected month.
3. **Run the investigation.** Watt binds the run to the selected snapshot, month, and group. The findings area shows the current check and completed checks. The analyst can cancel or reopen the run.
4. **Read the report.** The report leads with the reported movement, follows with the breakdown, and marks unresolved causes. The analyst opens supporting calculations or records in place. Market and weather context and the activity log expand on demand.
5. **Decide what to do next.** The analyst can leave an item open, attach a dated record to a specific contract, or ask a follow-up. A retention comparison uses separate assumptions entered by the analyst.

## 5. Functional requirements and acceptance criteria

Priorities describe product importance. P0 failures block demo acceptance. P1 features are included in the demo and should pass their own acceptance checks.

| ID | Priority | Requirement and acceptance criteria |
| --- | --- | --- |
| FIN-01 | P0 | **Snapshot and period.** The November snapshot contains postings through November. Refresh selects the prepared December snapshot. Switching the reporting month within that snapshot updates the comparison and trend endpoint without changing the snapshot. An unavailable group or period produces an explicit error. |
| FIN-02 | P0 | **Margin basis.** Reported margin includes adjustments in the month posted. Normalized margin excludes identified adjustments for an earlier service period. A November service charge posted in December appears in December reported margin and is excluded from December normalized margin. Investigations use reported margin and the display toggle explains this. |
| FIN-03 | P0 | **Reconciliation and drill-down.** Contract-month amounts sum exactly to contract, group, and portfolio totals at the relevant scope. Group rows show size, margin per customer, margin, and movement. Solar status and winter usage remain independent attributes. Include incomplete classifications in the reconciliation. Contract views distinguish realized margin to date from completed totals and show missing monthly coverage. |
| FIN-04 | P0 | **Materiality.** Flag changes of at least $1,000 and 10% of absolute prior reported margin, or a sign change with a movement of at least $1,000. A flag offers a shortcut. Any available group can be selected for investigation. |
| INV-01 | P0 | **Run lifecycle.** Record snapshot, reporting month, group, and run ID on launch. Display queued status and actual streamed checks. A browser reload restores the run. Cancellation produces an explicit outcome. Rerunning creates a new run linked to the original scope and history. |
| INV-02 | P0 | **Report and evidence.** Show the reported movement and any supported or unresolved contributions in one report. Each material statement links to a calculation or applicable evidence. For document evidence, show source and date where available. Test that a future publication, stale revision, and wrong-contract record cannot substantiate a finding. |
| INV-03 | P0 | **Gaps and failure.** Preserve verified findings when an investigation ends partially. Label the outcome and its reason. An empty or failed run gives a useful status and rerun path. When lower imports are observed without a verified cause, the report keeps that cause open. Regional weather and market notices appear as context unless evidence supports attribution. |
| REV-01 | P1 | **Analyst evidence.** A dated record for an eligible contract creates a child revision with its source and a parent link. Opening the original shows the original findings. Evidence for one contract can update that contract’s review without establishing a cause for the entire group. |
| REV-02 | P1 | **Follow-up.** Answer supported questions from saved findings with amounts, statuses, and source references. A question about move-outs returns an unresolved answer when the saved evidence cannot establish a move. Questions outside the supported scope receive a clear response. |
| DEC-01 | P1 | **Retention comparison.** Accept explicit assumptions for cohort size, contribution if retained, stay probabilities, outreach cost, and incentive. Show expected contribution with and without the offer, incremental contribution, and the break-even threshold or its infeasibility. Surface the usage caveat when relevant. |
| OPS-01 | P0 | **Local delivery.** A fresh checkout can seed the demo data, start the workspace, authenticate the agent, and reproduce the core flow from the README. Restarting the API preserves saved reports. Customer and contract records are fictional. Public evidence carries separate provenance. |

### Golden acceptance case

After **Refresh snapshot**, December reported portfolio margin is **$570,322.95**, a decline of **$1,000**. High Winter Usage contributes **+$2,200**, Low Winter Usage **−$800**, and Solar **−$2,400**. The Solar report attributes **−$1,200** to higher export credits and **−$900** to a prior-period settlement charge. **−$300** is associated with lower recorded imports whose cause remains open. The normalized portfolio total is **$571,222.95**, a decline of **$100**. A reviewer must be able to open the settlement record and verify the posting and service months.

## 6. Success measures and evaluation

**Primary outcome.** Reduce analyst time from receiving the monthly snapshot to producing a defensible explanation of a material movement. A defensible explanation reconciles to the posted total, cites evidence for each stated cause, and marks missing evidence explicitly.

| Measure | Definition | Proposed pilot criterion |
| --- | --- | --- |
| Time to defensible finding | Elapsed time from opening the assigned snapshot to submitting a report that passes finance review. | At least 30% lower median time than matched workbook tasks. |
| Financial accuracy | Compare portfolio, group, and sampled contract results to finance-approved figures for the same scope and basis. | Exact agreement in cents across the pilot acceptance set. |
| Evidence quality | Audit each material causal claim for applicable source, date, scope, and support. | Zero unsupported material causal claims in the audited set. |
| Analyst usability | Analyst independently identifies the main driver, opens its source, and explains what remains unresolved. | At least 80% of participants complete all three tasks without coaching. |
| Run reliability | Track completed, partial, and failed runs separately, with the reason and time spent queued. | Establish the baseline during shadow close. Agree on acceptable partial and failure rates before expanding access. |
| Responsiveness | Measure time to visible portfolio results and launch-to-terminal latency under pilot load. | Aim for a warm portfolio response within two seconds and typical investigations within 90 seconds. |

For a proposed first study, recruit five to eight analysts. Give each matched close tasks in Watt and their existing workflow, vary the order, and have a finance reviewer score submissions against the same rubric. Include a clear adjustment, offsetting group movements, and a case with missing evidence. Record time, errors, and intervention points. The demo has verified fixtures and workflow behavior. These pilot targets are hypotheses pending a baseline.

**Pilot instrumentation.** Capture snapshot-opened, run-started, run-ended, evidence-opened, and revision-created events. Include time, snapshot, reporting month, group, and run ID as needed for measurement. Record outcome and reason at run end. Use the existing run history for worker progress and add only the events needed to measure the workflow. Exclude customer identifiers and raw evidence text from analytics.

## 7. Dependencies, tradeoffs, and risks

| Decision or risk | Product implication and response |
| --- | --- |
| Deterministic arithmetic and bounded agent tools | SQL and Python own the dollars. Codex collects evidence and selects findings through scoped read-only tools. This makes amounts and claims auditable, with limited coverage of unfamiliar drivers. Expand the source and cause set against reviewed cases. |
| Source freshness and applicability | A document or weather observation published after the cutoff can change the story in hindsight. Track provenance and dates, and evaluate stale, missing, and mis-scoped sources. |
| Prepared data and local execution | The demo is reproducible. Actual data may have missing records, inconsistent mappings, and revised postings. Validate the finance definition and feed quality before ingesting live records. |
| Model variability and worker availability | Runs can finish partially or wait in the queue. Preserve verified results, show the outcome clearly, and measure queue time and reliability. Compare model configurations on the same evidence tasks before pinning a pilot default. |
| Sensitive company and customer records | Real data access depends on approved source fields, identity and role controls, retention rules, and provider data-handling review. Use read-only feeds and a separate application-state store. |
| Misuse of retention scenarios | The expected value depends on input assumptions. Display the assumptions and break-even. Any claim about offer effectiveness requires separate intervention evidence. |

Technical contracts, financial definitions, and verification commands live in the [design](design.md) and [README](../README.md).

## 8. Rollout and decision gates

| Stage | Deliverable | Exit criteria and proposed owner |
| --- | --- | --- |
| Local demo | Reproducible synthetic month-end workflow and recorded walkthrough. | Engineering runs the reconciliation, retrieval, agent, persistence, and browser checks. Product rehearses the golden case and a partial-result case. [Verification history](../PROGRESS.md) |
| Discovery | Document one team’s close workflow, evidence sources, and current time to a reviewed explanation. | Product and finance confirm a recurring problem, agree on the first portfolio and margin definition, and set a baseline. |
| Shadow close | Use one approved portfolio with read-only inputs alongside the existing close process. | Finance signs off on reconciliation and the evidence audit. Data and security owners approve source scope, access, and retention. Product reviews study results and run reliability. |
| Limited pilot | Give the selected analysts access over two reporting cycles. | Finance and product review accuracy, time saved, usability, and incomplete runs before deciding whether to expand. If reporting totals diverge or an unsupported material claim reaches a report, pause use for that scope and use the existing close process while investigating. |

After the pilot, prioritize the bottleneck observed in practice. Add feed coverage when analysts lack inputs, a handoff or export when results are hard to share, and semantic retrieval when evidence tests show material keyword-search misses.

## 9. Open product decisions

| Decision | Proposed decision maker | Evidence needed |
| --- | --- | --- |
| Which portfolio and margin definition should anchor the pilot? | Finance sponsor and data owner | An approved close package, account mappings, and examples of prior-period adjustments. |
| What counts as material in each portfolio? | Finance lead | Historical movements and examples that warranted escalation. |
| Who owns each unresolved item and where should it be handed off? | Finance, pricing, and supply leads | Examples of how open items are assigned, resolved, and documented today. |
| Which evidence and fields may be used by the agent, and how long should reports persist? | Data owner and security | Source access requirements, retention rules, and approved runtime configuration. |
| Does retention modeling belong in the close workflow? | Product and commercial lead | Evidence that analysts use the margin explanation to make or support an offer decision. |
