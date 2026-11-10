"""One local worker. Child SDK calls have a wall-clock limit and no state credentials."""
import json
import os
import selectors
import signal
import subprocess
import sys
import time

from psycopg.types.json import Jsonb
from .workflow import event, load, state


def claim():
    with state() as conn:
        row = conn.execute("""UPDATE watt_workflow.run SET status='running', updated_at=now()
            WHERE id=(SELECT id FROM watt_workflow.run WHERE status='queued'
                ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING *""").fetchone()
        if row:
            event(conn, row["id"], "running", "Starting scoped investigation")
        return row


def finish(run_id, status, findings, text):
    with state() as conn:
        changed = conn.execute("""UPDATE watt_workflow.run SET status=%s, findings=coalesce(%s, findings), message=%s,
            updated_at=now() WHERE id=%s AND status='running' RETURNING id""",
            (status, Jsonb(findings) if findings is not None else None, text, run_id)).fetchone()
        if changed:
            event(conn, run_id, status, text)


def run_job(row):
    run_id = row["id"]
    child_env = {key: value for key, value in os.environ.items()
                 if not key.startswith("PG") and key not in {
                     "WATT_STATE_DSN", "WATT_STATE_PASSWORD", "WATT_DB_PASSWORD",
                     "WATT_READER_PASSWORD", "OPENAI_API_KEY", "CODEX_API_KEY"}}
    started = time.monotonic()
    with subprocess.Popen(
        [sys.executable, "-m", "watt.codex_investigator", json.dumps(row["scope"])],
        env=child_env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
    ) as proc, selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ)
        pending, latest = b"", []
        try:
            while True:
                with state() as conn:
                    if load(conn, run_id)["status"] != "running":
                        return
                if time.monotonic() - started >= 300:
                    finish(run_id, "partial", latest, "Five-minute investigation limit reached")
                    return
                if not selector.select(timeout=1):
                    continue
                data = os.read(proc.stdout.fileno(), 65536)
                if not data:
                    finish(run_id, "failed", latest, "Codex exited before returning a verified result")
                    return
                pending += data
                while b"\n" in pending:
                    raw, pending = pending.split(b"\n", 1)
                    item = json.loads(raw)
                    kind = item["kind"]
                    if kind == "checkpoint":
                        latest = item["findings"]
                        with state() as conn:
                            conn.execute("""UPDATE watt_workflow.run SET findings=%s
                                WHERE id=%s AND status='running'""", (Jsonb(latest), run_id))
                    elif kind in {"result", "partial", "failed"}:
                        finish(run_id, "completed" if kind == "result" else kind,
                               item.get("findings", latest), item.get("text", "Verified findings ready"))
                        return
                    elif kind in {"verified", "tool", "checked"}:
                        with state() as conn:
                            event(conn, run_id, kind, item["text"])
        finally:
            # The SDK launches child processes of its own; bound the entire run.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()


def main():
    with state(autocommit=True) as lock:
        if not lock.execute("SELECT pg_try_advisory_lock(20251110)").fetchone()["pg_try_advisory_lock"]:
            raise SystemExit("Another Watt worker is already running")
        with lock.transaction():
            rows = lock.execute("""UPDATE watt_workflow.run SET status='interrupted',updated_at=now(),
                message='Worker restarted before completion' WHERE status='running' RETURNING id""").fetchall()
            for row in rows:
                event(lock, row["id"], "interrupted", "Worker restarted before completion")
        print("Watt investigator worker ready", flush=True)
        while True:
            row = claim()
            if not row:
                time.sleep(1)
                continue
            try:
                run_job(row)
            except Exception:
                finish(row["id"], "failed", None, "Worker could not complete the investigation")


if __name__ == "__main__":
    main()
