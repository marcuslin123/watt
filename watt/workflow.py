"""PostgreSQL-backed queue and browser-facing run state."""
from contextlib import contextmanager
import os
from uuid import uuid4, UUID
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .db import reporting
from .decisions import Resolution, Scenario, apply_resolution, calculate_scenario, follow_up
from .investigation import Scope

router = APIRouter(prefix="/api/investigations")
ACTIVE = {"queued", "running"}


@contextmanager
def state(*, autocommit=False):
    dsn = os.environ.get("WATT_STATE_DSN")
    if not dsn:
        raise HTTPException(503, "Set WATT_STATE_DSN for investigation state")
    try:
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=4,
                             autocommit=autocommit) as conn:
            yield conn
    except psycopg.Error as exc:
        raise HTTPException(503, "Investigation database unavailable") from exc


def event(conn, run_id, kind, text):
    conn.execute("INSERT INTO watt_workflow.event (run_id,kind,text) VALUES (%s,%s,%s)",
                 (run_id, kind, text))


def load(conn, run_id):
    row = conn.execute("SELECT * FROM watt_workflow.run WHERE id=%s", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Investigation not found")
    return row


def enqueue(scope, parent=None):
    run_id = uuid4()
    with state() as conn:
        conn.execute("INSERT INTO watt_workflow.run (id,scope,parent_id,status) VALUES (%s,%s,%s,'queued')",
                     (run_id, Jsonb(scope.model_dump(mode="json")), parent))
        event(conn, run_id, "queued", "Investigation queued")
    return {"id": run_id, "status": "queued"}


@router.post("", status_code=202)
def start(scope: Scope):
    with reporting() as conn:
        row = conn.execute("""SELECT 1 FROM watt_reporting.group_month
            WHERE snapshot=%s AND posting_month=%s AND customer_group=%s""",
            (scope.snapshot, scope.month, scope.group)).fetchone()
    if row is None:
        raise HTTPException(404, "This group and month are not available in the snapshot")
    return enqueue(scope)


@router.get("/{run_id}")
def detail(run_id: UUID):
    with state() as conn:
        row = load(conn, run_id)
        events = conn.execute("""SELECT id, kind, text, created_at FROM watt_workflow.event
            WHERE run_id=%s ORDER BY id""", (run_id,)).fetchall()
    return {**row, "events": events}


@router.get("/{run_id}/stream")
def stream(run_id: UUID, after: int = 0):
    with state() as conn:
        load(conn, run_id)

    def messages():
        cursor = max(0, after)
        # Reconnect with the same persisted cursor after 25 seconds.
        for _ in range(25):
            with state() as conn:
                row = load(conn, run_id)
                pending = conn.execute("""SELECT id,kind,text,created_at FROM watt_workflow.event
                    WHERE run_id=%s AND id>%s ORDER BY id""", (run_id, cursor)).fetchall()
            for entry in pending:
                cursor = entry["id"]
                yield f"data: {json.dumps(entry, default=str)}\n\n"
            if row["status"] not in ACTIVE:
                yield 'event: terminal\ndata: {}\n\n'
                return
            if not pending:
                yield ": waiting\n\n"
            time.sleep(1)

    return StreamingResponse(messages(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{run_id}/cancel")
def cancel(run_id: UUID):
    with state() as conn:
        changed = conn.execute("""UPDATE watt_workflow.run SET status='cancelled', updated_at=now()
            WHERE id=%s AND status IN ('queued','running') RETURNING id""", (run_id,)).fetchone()
        if changed:
            event(conn, run_id, "cancelled", "Cancelled by analyst")
        return {"status": load(conn, run_id)["status"]}


@router.post("/{run_id}/rerun", status_code=202)
def rerun(run_id: UUID):
    with state() as conn:
        row = load(conn, run_id)
    if row["status"] in ACTIVE:
        raise HTTPException(409, "Finish or cancel this run before rerunning")
    return enqueue(Scope.model_validate(row["scope"]), run_id)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@router.post("/{run_id}/review", status_code=201)
def review(run_id: UUID, resolution: Resolution):
    revision = uuid4()
    with state() as conn:
        row = load(conn, run_id)
        if row["status"] not in {"completed", "partial"}:
            raise HTTPException(409, "Only runs with reviewable results can be revised")
        try:
            findings = apply_resolution(row["findings"], Scope.model_validate(row["scope"]).month,
                                        resolution, revision)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        conn.execute("""INSERT INTO watt_workflow.run (id,scope,parent_id,status,findings,message)
            VALUES (%s,%s,%s,%s,%s,'Analyst evidence recorded; original run preserved')""",
            (revision, Jsonb(row["scope"]), run_id, row["status"], Jsonb(findings)))
        event(conn, revision, "reviewed", "Analyst record attached to the usage finding")
    return {"id": revision, "parent_id": run_id, "status": row["status"]}


@router.post("/{run_id}/follow-up")
def answer(run_id: UUID, question: Question):
    with state() as conn:
        row = load(conn, run_id)
    return follow_up(row["findings"], question.question)


@router.post("/{run_id}/scenario")
def scenario(run_id: UUID, assumptions: Scenario):
    with state() as conn:
        row = load(conn, run_id)
    if row["status"] not in {"completed", "partial"} or not row["findings"]:
        raise HTTPException(409, "Run the investigation before comparing a scenario")
    return {**calculate_scenario(assumptions), "scope": row["scope"],
            "usage_unresolved": any(item["key"] == "usage" and item["status"] == "unresolved"
                                    for item in row["findings"])}
