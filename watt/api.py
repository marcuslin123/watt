"""Local HTTP interface for Watt's PostgreSQL reporting views."""
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from .db import reporting

app = FastAPI(title="Watt")
Snapshot = Literal["initial", "refreshed"]
Group = Literal["solar", "high_winter", "low_winter", "unclassified"]


def fetch(conn, sql, *params):
    return conn.execute(sql, params).fetchall()


def int_fields(row, fields):
    return {**row, **{key: int(row[key]) for key in fields if row[key] is not None}}


def is_material(previous: int, current: int) -> bool:
    delta = abs(current - previous)
    sign_change = previous < 0 < current or current < 0 < previous
    return delta >= 100000 and (sign_change or delta * 10 >= abs(previous))


@app.get("/api/health")
def health():
    with reporting() as conn:
        conn.execute("SELECT 1 FROM watt_reporting.snapshots LIMIT 1").fetchone()
    return {"status": "ready"}


@app.get("/api/snapshots")
def snapshots():
    with reporting() as conn:
        return fetch(conn, "SELECT snapshot, cutoff FROM watt_reporting.snapshots ORDER BY cutoff")


@app.get("/api/portfolio")
def portfolio(snapshot: Snapshot = "initial", month: date | None = None):
    with reporting() as conn:
        raw = fetch(conn, """SELECT posting_month AS month, reported, normalized
            FROM watt_reporting.portfolio_month WHERE snapshot=%s ORDER BY posting_month""", snapshot)
        if not raw:
            raise HTTPException(404, "Snapshot has no reporting months")
        rows = [int_fields(row, ("reported", "normalized")) for row in raw]
        selected = month or rows[-1]["month"]
        through = [r for r in rows if r["month"] <= selected]
        if not through or through[-1]["month"] != selected:
            raise HTTPException(404, "Month is outside this snapshot")
        current = through[-1]
        previous = through[-2] if len(through) > 1 else None
        previous_month = previous["month"] if previous else None
        group_rows = fetch(conn, """SELECT posting_month, customer_group AS "group",
            reported, normalized, customer_count FROM watt_reporting.group_month
            WHERE snapshot=%s AND posting_month IN (%s, %s)""", snapshot, selected, previous_month)
        groups = {}
        for row in group_rows:
            groups.setdefault(row["group"], {})[row["posting_month"]] = row
        items = []
        for name, by_month in sorted(groups.items()):
            now = by_month.get(selected, {})
            prior = by_month.get(previous_month, {})
            r, n = int(now.get("reported", 0)), int(now.get("normalized", 0))
            p, pn = int(prior.get("reported", 0)), int(prior.get("normalized", 0))
            items.append({"group": name, "reported": r, "normalized": n,
                          "customer_count": now.get("customer_count", 0),
                          "delta": r - p if previous else None,
                          "normalized_delta": n - pn if previous else None,
                          "flagged": is_material(p, r) if previous else False})
    return {**current, "snapshot": snapshot, "cutoff": rows[-1]["month"],
            "previous_month": previous_month,
            "delta": current["reported"] - previous["reported"] if previous else None,
            "normalized_delta": current["normalized"] - previous["normalized"] if previous else None,
            "groups": items, "trend": through[-12:], "months": [r["month"] for r in rows]}


@app.get("/api/contracts")
def contracts(snapshot: Snapshot, month: date, group: Group, q: str = Query("", max_length=80),
              offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    # Literal substring matches only; '%' and '_' are not wildcards.
    with reporting() as conn:
        rows = fetch(conn, """SELECT contract_id, customer_id, plan, reported, normalized
            FROM watt_reporting.contract_month WHERE snapshot=%s AND posting_month=%s
              AND customer_group=%s AND (strpos(lower(contract_id), lower(%s)) > 0 OR %s = '')
            ORDER BY contract_id LIMIT %s OFFSET %s""",
            snapshot, month, group, q, q, limit + 1, offset)
    return {"items": [int_fields(row, ("reported", "normalized")) for row in rows[:limit]],
            "has_more": len(rows) > limit}


@app.get("/api/contracts/{contract_id}")
def contract_detail(contract_id: str, snapshot: Snapshot):
    with reporting() as conn:
        rows = fetch(conn, """SELECT contract_id, customer_id, starts, ends, reported, normalized,
            observed_count, missing_count, completed_margin FROM watt_reporting.contract_total
            WHERE snapshot=%s AND contract_id=%s""", snapshot, contract_id)
        if not rows:
            raise HTTPException(404, "Contract not available in this snapshot")
        total = int_fields(rows[0], ("reported", "normalized", "missing_count", "completed_margin"))
        months = fetch(conn, """SELECT posting_month AS month, reported, normalized,
            imported_kwh, exported_kwh, plan, customer_group AS "group", energy_revenue,
            fixed_fees, bill_credits, export_credits, wholesale, ancillary, transmission, other
            FROM watt_reporting.contract_month WHERE snapshot=%s AND contract_id=%s ORDER BY posting_month DESC""",
            snapshot, contract_id)
        adjustments = fetch(conn, """SELECT evidence_id, posting_month, service_month, component, cost_cents
            FROM watt_reporting.adjustments WHERE snapshot=%s AND contract_id=%s ORDER BY posting_month, evidence_id""",
            snapshot, contract_id)
    return {**total, "snapshot": snapshot,
            "months": [int_fields(row, ("reported", "normalized")) for row in months],
            "adjustments": adjustments}


from .workflow import router as investigations

app.include_router(investigations)
