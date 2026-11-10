# Watt Margin Foundation Implementation Plan

**Goal:** Generate the approved synthetic portfolio and prove monthly, contract, group, and portfolio margins reconcile.

**Spec:** [Watt design](../../design.md). This milestone stops before database loading, UI, and agent integration.

- Write tests for exact cent arithmetic, signed prior-period adjustments, duplicate protection, snapshot cutoffs, contract coverage, winter grouping, and the agreed demo deltas.
- Implement a standard-library Python margin module using integer cents as fixed-point currency. Roll up the same validated rows independently by month, group, and contract. Carry incomplete coverage and unclassified dollars explicitly.
- Generate stable synthetic contracts and contract-month records; add an on-demand JSON Lines export with snapshot metadata rather than checking in the large dataset.
- Run the reconciliation suite and export the full fixture. Record actual results and runnable commands.
