"""Verify an earlier browser walkthrough after restarting the API process."""
import json
import os
from urllib.request import urlopen

from .workflow import state


def main():
    # The state-role query is read-only; the API independently fetches both runs.
    with state() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        revision = conn.execute("""
            SELECT r.id, r.parent_id FROM watt_workflow.run r
            WHERE EXISTS (SELECT 1 FROM watt_workflow.event e
                          WHERE e.run_id=r.id AND e.kind='reviewed')
            ORDER BY r.created_at DESC LIMIT 1
        """).fetchone()
    if not revision:
        raise SystemExit("Run the live browser walkthrough before checking persistence")
    origin = os.environ.get("WATT_API_ORIGIN", "http://127.0.0.1:8000").rstrip("/")

    def load(run_id):
        with urlopen(f"{origin}/api/investigations/{run_id}", timeout=10) as response:
            return json.load(response)

    parent, child = load(revision["parent_id"]), load(revision["id"])
    assert parent["status"] == child["status"] == "completed"
    assert child["parent_id"] == parent["id"]
    original = {row["key"]: row for row in parent["findings"]}
    updated = {row["key"]: row for row in child["findings"]}
    assert set(original) == set(updated)
    assert all(original[key] == updated[key] for key in original if key != "usage")
    assert original["usage"]["amount_cents"] == updated["usage"]["amount_cents"] == -30000
    assert updated["usage"]["status"] == "unresolved"
    assert not any(item["tool"] == "analyst" for item in original["usage"]["evidence"])
    assert any(item.get("record", {}).get("provenance") == "analyst supplied"
               for item in updated["usage"]["evidence"])
    assert any(row["kind"] == "reviewed" for row in child["events"])
    assert sum(row["kind"] == "checked" for row in parent["events"]) == 5
    print("Restarted API restored the original live findings and the isolated analyst revision.")


if __name__ == "__main__":
    main()
