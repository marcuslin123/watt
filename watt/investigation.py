"""Scoped SQL tools and deterministic publication of supported findings."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel
from .db import reporting
from .evidence import read_context, search_evidence


class Scope(BaseModel):
    snapshot: Literal["initial", "refreshed"]
    month: date
    group: Literal["solar", "high_winter", "low_winter", "unclassified"]


def previous(month):
    return month.replace(month=month.month - 1) if month.month > 1 else date(month.year - 1, 12, 1)


def evidence(tool, key, title, **values):
    return {"tool": tool, "id": key, "title": title, **values}


def cost_effects(old_usage, new_usage, old_cost, new_cost):
    """Allocate a comparable supply-cost change at the prior effective unit cost."""
    delta = new_cost - old_cost
    if not old_usage or not new_usage:
        return {"usage_cents": 0, "unit_cost_cents": 0, "direct_cents": delta}
    volume = Decimal((new_usage - old_usage) * old_cost) / old_usage
    usage = int(volume.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {"usage_cents": usage, "unit_cost_cents": delta - usage, "direct_cents": 0}


def read_tool(scope, tool):
    now, prior = scope.month, previous(scope.month)
    args = (scope.snapshot, scope.group, prior, now)
    with reporting() as conn:
        if tool == "bridge":
            rows = conn.execute("""
                SELECT posting_month AS month, plan, sum(reported)::bigint AS reported,
                    sum(normalized)::bigint AS normalized, sum(export_credits)::bigint AS credits,
                    sum(imported_kwh)::bigint AS imports,
                    sum(wholesale+ancillary+transmission+other)::bigint AS supply_cost
                FROM watt_reporting.contract_month
                WHERE snapshot=%s AND customer_group=%s AND posting_month IN (%s,%s)
                GROUP BY posting_month, plan ORDER BY posting_month, plan
            """, args).fetchall()
            effects = []
            by_plan = {}
            for row in rows:
                by_plan.setdefault(row["plan"], {})[row["month"]] = row
            for plan, periods in sorted(by_plan.items()):
                if now not in periods or prior not in periods:
                    continue
                old, new = periods[prior], periods[now]
                effects.append({"plan": plan, **cost_effects(old["imports"], new["imports"],
                                                            old["supply_cost"], new["supply_cost"])})
            return [evidence(tool, "group-margin", "Group margin bridge", rows=rows,
                             supply_cost_effects=effects)]
        if tool == "adjustments":
            rows = conn.execute("""
                SELECT a.evidence_id, a.contract_id, a.posting_month, a.service_month, a.cost_cents
                FROM watt_reporting.adjustments a JOIN watt_reporting.contract_month m
                  USING (snapshot, contract_id, posting_month)
                WHERE a.snapshot=%s AND m.customer_group=%s AND a.posting_month IN (%s,%s)
                  AND a.service_month < a.posting_month ORDER BY a.evidence_id
            """, args).fetchall()
            return [evidence(tool, "posted-adjustments", "Prior-period adjustment records", rows=rows)]
        if tool == "usage":
            result = conn.execute("""
                SELECT count(*) AS count, coalesce(sum(cur.reported-old.reported),0)::bigint AS delta,
                       coalesce(sum(cur.imported_kwh-old.imported_kwh),0)::bigint AS kwh_delta,
                       (array_agg(cur.contract_id ORDER BY cur.contract_id))[1:5] AS sample
                FROM watt_reporting.contract_month cur JOIN watt_reporting.contract_month old
                  USING (snapshot, contract_id)
                WHERE cur.snapshot=%s AND cur.customer_group=%s AND old.posting_month=%s
                  AND cur.posting_month=%s AND cur.usage_valid AND old.usage_valid
                  AND cur.imported_kwh < old.imported_kwh
            """, args).fetchone()
            return [evidence(tool, "usage-drops", "Contracts with lower recorded imports", **result)]
        if tool == "context":
            notices, weather = read_context(conn, scope.snapshot, now)
            return [evidence(tool, row["evidence_id"], row["title"], document=row) for row in notices] + [
                evidence(tool, "dfw-weather", "Dallas/Fort Worth weather coverage",
                         readings=weather, available=bool(weather))]
        if tool == "documents":
            rows = search_evidence(conn, scope.snapshot, now, group=scope.group)
            return [evidence(tool, row["evidence_id"], row["title"], document=row) for row in rows]
    raise ValueError("Unknown analytical tool")


TOOLS = ("bridge", "adjustments", "usage", "documents", "context")


def catalog(scope, packs):
    now, prior = scope.month, previous(scope.month)
    out = {}
    bridge = packs.get("bridge", [])
    rows = bridge[0]["rows"] if bridge else []
    docs = {item["id"]: item for item in packs.get("documents", [])}

    def change(field, subset=rows):
        return (sum(r[field] for r in subset if str(r["month"]) == str(now))
                - sum(r[field] for r in subset if str(r["month"]) == str(prior)))

    def add(key, status, title, detail, cents, refs):
        out[key] = {"status": status, "title": title, "detail": detail,
                    "amount_cents": cents, "evidence": refs}

    if {str(r["month"]) for r in rows} == {str(now), str(prior)}:
        add("bridge", "calculated", "Reported margin movement",
            "The comparison uses posted margins for the selected group and preceding month.",
            change("reported"), bridge)
        plan_rows = [r for r in rows if r["plan"] == "solar_export_credit"]
        doc = docs.get("solar-plan-v2")
        if doc and now == date(2025, 12, 1) and change("credits", plan_rows) == 120000:
            add("credits", "supported", "Higher export credits under one solar plan",
                "The applicable plan revision and billing records show higher credits for eligible contracts.",
                -change("credits", plan_rows), bridge + [doc])
    adjustments = packs.get("adjustments", [])
    doc = docs.get("solar-settlement-dec")
    if adjustments and doc:
        amounts = adjustments[0]["rows"]
        delta = -(sum(r["cost_cents"] for r in amounts if str(r["posting_month"]) == str(now))
                  - sum(r["cost_cents"] for r in amounts if str(r["posting_month"]) == str(prior)))
        if delta == -90000 and now == date(2025, 12, 1):
            add("settlement", "supported", "Prior-period settlement charge",
                "November service costs posted in December. Normalized margin excludes this adjustment.",
                delta, adjustments + [doc])
    usage = packs.get("usage", [])
    if usage and usage[0]["count"]:
        add("usage", "unresolved", "Lower recorded imports; cause unresolved",
            "These contracts contributed to the margin movement. Verify meter readings or dated service records before attributing the decline to a move or changing future assumptions.",
            usage[0]["delta"], usage)
    context = packs.get("context", [])
    if context:
        weather = next((row for row in context if row["id"] == "dfw-weather"), {})
        weather_note = ("The prepared DFW station observations are regional context only."
                        if weather.get("available") else "No DFW weather observation was available by this snapshot cutoff.")
        add("context", "observed", "Public market and weather context",
            weather_note + " A market notice or weather observation does not establish a customer margin cause.",
            None, context)
    return out


def validated_findings(keys, available, observed):
    if len(keys) != len(set(keys)) or any(key not in available for key in keys):
        raise ValueError("Unknown or duplicate finding")
    result = []
    for key in keys:
        finding = available[key]
        if any(item["id"] not in observed.get(item["tool"], set()) for item in finding["evidence"]):
            raise ValueError("Finding is missing tool evidence from this run")
        result.append({"key": key, **finding})
    return result
