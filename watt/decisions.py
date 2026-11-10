"""Analyst-owned evidence and deterministic, explicitly assumed scenarios."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import re

from pydantic import BaseModel, ConfigDict, Field


class Scenario(BaseModel):
    customers: int = Field(ge=1, le=10000)
    contribution_cents: int = Field(ge=-10_000_000, le=10_000_000)
    baseline_bps: int = Field(ge=0, le=10000)
    offer_bps: int = Field(ge=0, le=10000)
    outreach_cents: int = Field(ge=0, le=10_000_000)
    incentive_cents: int = Field(ge=0, le=10_000_000)


def calculate_scenario(scenario):
    a = scenario
    scale = Decimal(10000)
    baseline = Decimal(a.customers * a.baseline_bps * a.contribution_cents) / scale
    offer = a.customers * (Decimal(a.offer_bps * (a.contribution_cents - a.incentive_cents))
                          / scale - a.outreach_cents)
    denominator = a.contribution_cents - a.incentive_cents
    needed = a.baseline_bps * a.contribution_cents + 10000 * a.outreach_cents
    # Look for a break-even probability at or above the no-offer baseline.
    threshold = None
    if a.baseline_bps * denominator >= needed:
        threshold = a.baseline_bps
    elif denominator > 0:
        required = int((Decimal(needed) / denominator).to_integral_value(rounding=ROUND_CEILING))
        if required <= 10000:
            threshold = max(required, a.baseline_bps)

    def cents(amount):
        return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    baseline_cents, offer_cents = cents(baseline), cents(offer)
    return {
        "baseline_cents": baseline_cents, "offer_cents": offer_cents,
        "incremental_cents": offer_cents - baseline_cents, "break_even_offer_bps": threshold,
        "required_uplift_bps": None if threshold is None else threshold - a.baseline_bps,
        "assumptions": a.model_dump(),
    }


class Resolution(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    contract_id: str = Field(pattern=r"^contract-[0-9]{5}$")
    record_date: date
    source: str = Field(min_length=4, max_length=120)
    note: str = Field(min_length=12, max_length=600)


def apply_resolution(findings, month, resolution, revision_id):
    revised = deepcopy(findings)
    usage = next((row for row in revised if row["key"] == "usage" and row["status"] == "unresolved"), None)
    if not usage:
        raise ValueError("This run has no unresolved usage finding")
    scoped = next((item for item in usage["evidence"] if item["id"] == "usage-drops"), None)
    if not scoped or resolution.contract_id not in (scoped.get("sample") or []):
        raise ValueError("Choose a contract listed in the run’s usage evidence")
    last_day = month.replace(day=monthrange(month.year, month.month)[1])
    if not month <= resolution.record_date <= last_day:
        raise ValueError("Evidence date must be inside the selected reporting month")
    supplied = [item["record"]["contract_id"] for item in usage["evidence"] if item.get("tool") == "analyst"]
    if resolution.contract_id in supplied:
        raise ValueError("This revision already contains a record for that contract")
    usage["evidence"].append({
        "tool": "analyst", "id": f"analyst-{revision_id}", "title": resolution.source,
        "record": {**resolution.model_dump(mode="json"), "provenance": "analyst supplied"},
    })
    usage["reviewed_contracts"] = sorted([*supplied, resolution.contract_id])
    remaining = scoped["count"] - len(usage["reviewed_contracts"])
    usage["detail"] = (f"Analyst supplied a dated record for {len(usage['reviewed_contracts'])} contract(s). "
                       f"{remaining} other contract(s) have no supplied record. "
                       "The supplied records are not independently verified; the group cause and historical amounts are unchanged.")
    return revised


def follow_up(findings, question):
    # Limit the demo to questions that can be answered from this saved investigation.
    words = set(re.findall(r"[a-z]+", question.lower()))
    if words & {"hedge", "trading", "trade", "forecast", "predict", "tomorrow"}:
        keys = set()
    elif words & {"move", "moved", "imports", "usage", "meter"}:
        keys = {"usage"}
    elif words & {"settlement", "adjustment", "normalized"}:
        keys = {"settlement"}
    elif words & {"ercot", "weather", "market"}:
        keys = {"context"}
    elif words & {"credit", "credits", "plan"}:
        keys = {"credits"}
    elif words & {"margin", "drivers", "decline", "change", "bridge", "evidence"}:
        keys = {row["key"] for row in findings}
    else:
        keys = set()
    rows = [{"title": row["title"], "amount_cents": row["amount_cents"], "status": row["status"],
             "detail": row["detail"], "sources": [item["id"] for item in row["evidence"]]}
            for row in findings if row["key"] in keys]
    return {"rows": rows,
            "message": "Based on this saved investigation." if rows
            else "This investigation cannot answer that question. Try asking about margin drivers, posted adjustments, credits, usage, or market context."}
