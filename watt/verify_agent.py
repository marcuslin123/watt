"""Live read-only evaluations of Codex output against the synthetic reporting data."""
import json
import subprocess
import sys

CASES = (
    ("December Solar", {"snapshot": "refreshed", "month": "2025-12-01", "group": "solar"},
     {"bridge": ("calculated", -240000), "settlement": ("supported", -90000),
      "credits": ("supported", -120000), "usage": ("unresolved", -30000)}),
    ("December High Winter", {"snapshot": "refreshed", "month": "2025-12-01", "group": "high_winter"},
     {"bridge": ("calculated", 220000)}),
)


def main():
    for name, scope, expected in CASES:
        completed = subprocess.run([sys.executable, "-m", "watt.codex_investigator", json.dumps(scope)],
                                   capture_output=True, text=True, timeout=90, check=True)
        events = list(map(json.loads, completed.stdout.splitlines()))
        result = events[-1]
        assert result["kind"] == "result", f"{name}: {result['kind']}"
        actual = {row["key"]: (row["status"], row["amount_cents"]) for row in result["findings"]}
        assert actual == expected, (name, actual)
        assert len([item for item in events if item["kind"] == "checked"]) == 4
        assert all(row["evidence"] for row in result["findings"])
        if name == "December Solar":
            refs = {row["key"]: {item["id"] for item in row["evidence"]} for row in result["findings"]}
            assert "solar-plan-v2" in refs["credits"]
            assert "solar-settlement-dec" in refs["settlement"]
            assert all("solar-plan-future" not in ids for ids in refs.values())
        print(f"{name}: live tools, findings, evidence and exact cents verified", flush=True)


if __name__ == "__main__":
    main()
