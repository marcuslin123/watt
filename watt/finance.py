"""Deterministic financial calculations at the contract-month grain.

All monetary fields are integer USD cents. Usage in the demo is whole kWh.
"""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from statistics import median
from typing import Iterable, Iterator

WINTER = (date(2024, 12, 1), date(2025, 1, 1), date(2025, 2, 1))
COSTS = ("wholesale", "ancillary", "transmission", "other")


@dataclass(frozen=True, slots=True)
class Contract:
    contract_id: str
    customer_id: str
    solar: bool | None
    starts: date
    ends: date  # Inclusive reporting month.
    plan: str = "standard"


@dataclass(frozen=True, slots=True)
class Adjustment:
    evidence_id: str
    service_month: date
    cost_cents: int
    component: str = "ancillary"


@dataclass(frozen=True, slots=True)
class Month:
    contract_id: str
    month: date  # Posting month; first day of the calendar month.
    billed_days: int
    imported_kwh: int
    exported_kwh: int
    energy_revenue: int = 0
    fixed_fees: int = 0
    bill_credits: int = 0
    export_credits: int = 0
    wholesale: int = 0
    ancillary: int = 0
    transmission: int = 0
    other: int = 0
    adjustments: tuple[Adjustment, ...] = ()
    usage_valid: bool = True


@dataclass(frozen=True, slots=True)
class Totals:
    reported: int
    normalized: int


@dataclass(frozen=True, slots=True)
class ContractTotal(Totals):
    observed_months: tuple[date, ...]
    missing_months: tuple[date, ...]
    completed_margin: int | None


@dataclass(frozen=True, slots=True)
class MonthlyTotal:
    portfolio: Totals
    groups: dict[str, Totals]


@dataclass(frozen=True, slots=True)
class Report:
    cutoff: date
    contracts: dict[str, ContractTotal]
    months: dict[date, MonthlyTotal]
    groups: dict[str, str]
    winter_profiles: dict[str, str | None]


def months_between(start: date, end: date) -> Iterator[date]:
    while start <= end:
        yield start
        if start == end:
            break
        start = date(start.year + (start.month == 12), start.month % 12 + 1, 1)


def margin(row: Month, *, normalized: bool = False) -> int:
    """Exclude only explicitly identified prior-service adjustments in normalized margin."""
    return (row.energy_revenue + row.fixed_fees - row.bill_credits - row.export_credits
            - sum(getattr(row, cost) for cost in COSTS)
            - sum(a.cost_cents for a in row.adjustments
                  if not normalized or a.service_month >= row.month))


def _validated(
    contracts: Iterable[Contract], rows: Iterable[Month], cutoff: date,
) -> tuple[dict[str, Contract], dict[str, dict[date, Month]]]:
    if cutoff.day != 1:
        raise ValueError("Snapshot cutoff must be a reporting month")
    catalog: dict[str, Contract] = {}
    for contract in contracts:
        if contract.contract_id in catalog:
            raise ValueError(f"Duplicate contract: {contract.contract_id}")
        if contract.starts.day != 1 or contract.ends.day != 1 or contract.starts > contract.ends:
            raise ValueError(f"Invalid contract interval: {contract.contract_id}")
        catalog[contract.contract_id] = contract
    by_contract: dict[str, dict[date, Month]] = {key: {} for key in catalog}
    evidence_ids = set()
    for row in rows:
        if row.month > cutoff:
            continue
        contract = catalog.get(row.contract_id)
        if (contract is None or row.month.day != 1
                or not contract.starts <= row.month <= contract.ends):
            raise ValueError(f"Invalid contract-month: {row.contract_id} {row.month}")
        entries = by_contract[row.contract_id]
        if row.month in entries:
            raise ValueError(f"Duplicate contract-month: {row.contract_id} {row.month}")
        if (not 0 <= row.billed_days <= monthrange(row.month.year, row.month.month)[1]
                or min(row.imported_kwh, row.exported_kwh) < 0):
            raise ValueError(f"Invalid usage quantities: {row.contract_id} {row.month}")
        for adj in row.adjustments:
            if (adj.evidence_id in evidence_ids or adj.component not in COSTS
                    or adj.service_month.day != 1
                    or not contract.starts <= adj.service_month <= row.month):
                raise ValueError(f"Invalid or duplicate adjustment: {adj.evidence_id}")
            evidence_ids.add(adj.evidence_id)
        entries[row.month] = row
    return catalog, by_contract


def _group_profiles(
    catalog: dict[str, Contract], rows: dict[str, dict[date, Month]],
) -> tuple[dict[str, str], dict[str, str | None]]:
    # Aggregate across contract changes, with one observation per customer-month.
    # Multiple contracts for the same customer-month are ambiguous for profiling.
    observations: dict[tuple[str, date], Month | None] = {}
    customers = {contract.customer_id for contract in catalog.values()}
    for key, contract in catalog.items():
        customer = contract.customer_id
        for period in WINTER:
            if period in rows[key]:
                obs_key = (customer, period)
                observations[obs_key] = None if obs_key in observations else rows[key][period]
    rates: dict[str, Fraction] = {}
    reference = []
    for customer in customers:
        winter = [observations.get((customer, period)) for period in WINTER]
        valid = [r for r in winter if r is not None and r.usage_valid
                 and r.billed_days == monthrange(r.month.year, r.month.month)[1]]
        if len(valid) == len(WINTER):
            rates[customer] = Fraction(sum(r.imported_kwh for r in valid),
                                       sum(r.billed_days for r in valid))
            if all(catalog[r.contract_id].solar is False for r in valid):
                reference.append(rates[customer])
    threshold = median(reference) if reference else None
    profiles = {
        customer: (None if threshold is None or customer not in rates
                   else "high_winter" if rates[customer] >= threshold else "low_winter")
        for customer in sorted(customers)
    }
    groups = {
        key: ("solar" if c.solar is True else
              (profiles[c.customer_id] or "unclassified") if c.solar is False
              else "unclassified")
        for key, c in catalog.items()
    }
    return groups, profiles


def classify(contracts: Iterable[Contract], rows: Iterable[Month], cutoff: date) -> dict[str, str]:
    return _group_profiles(*_validated(contracts, rows, cutoff))[0]


def analyze(contracts: Iterable[Contract], rows: Iterable[Month], cutoff: date) -> Report:
    catalog, by_contract = _validated(contracts, rows, cutoff)
    groups, profiles = _group_profiles(catalog, by_contract)
    contract_totals = {}
    monthly: dict[date, dict[str, list[int]]] = {}
    portfolio: dict[date, list[int]] = {}
    for key, entries in by_contract.items():
        contract = catalog[key]
        if contract.starts > cutoff:
            continue
        missing = tuple(m for m in months_between(contract.starts, min(contract.ends, cutoff))
                        if m not in entries)
        reported = normalized = 0
        for period, row in entries.items():
            actual, adjusted = margin(row), margin(row, normalized=True)
            reported += actual
            normalized += adjusted
            group_pair = monthly.setdefault(period, {}).setdefault(groups[key], [0, 0])
            total_pair = portfolio.setdefault(period, [0, 0])
            group_pair[0] += actual
            group_pair[1] += adjusted
            total_pair[0] += actual
            total_pair[1] += adjusted
        completed = reported if contract.ends <= cutoff and not missing else None
        contract_totals[key] = ContractTotal(
            reported, normalized, tuple(sorted(entries)), missing, completed,
        )
    periods = {
        period: MonthlyTotal(Totals(*portfolio[period]),
                             {name: Totals(*pair) for name, pair in monthly[period].items()})
        for period in sorted(monthly)
    }
    return Report(cutoff, contract_totals, periods, groups, profiles)
