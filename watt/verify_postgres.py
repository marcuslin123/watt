"""Reconcile the loaded PostgreSQL fixture against Python via psql."""
from collections import Counter
import csv
import io
import subprocess

from .finance import analyze, margin
from .synthetic import DECEMBER, NOVEMBER, make_demo


def query(sql: str) -> list[tuple[str, ...]]:
    result = subprocess.run(
        ["psql", "-X", "-q", "--csv", "-t", "-v", "ON_ERROR_STOP=1", "-c",
         "BEGIN READ ONLY; SET LOCAL ROLE watt_analyst; " + sql + "; ROLLBACK"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return list(map(tuple, csv.reader(io.StringIO(result.stdout))))


def verify() -> None:
    fixture = make_demo()
    observed = query("SELECT snapshot, count(*), max(posting_month) FROM watt_reporting.contract_month GROUP BY snapshot")
    assert set(observed) == {("initial", "230000", "2025-11-01"),
                            ("refreshed", "240000", "2025-12-01")}, observed
    for snapshot, cutoff in (("initial", NOVEMBER), ("refreshed", DECEMBER)):
        reference = analyze(fixture.contracts, fixture.months, cutoff)
        expected_groups = {
            (str(period), group, str(total.reported), str(total.normalized))
            for period, month in reference.months.items() for group, total in month.groups.items()
        }
        expected_portfolio = {(str(period), str(month.portfolio.reported), str(month.portfolio.normalized))
                              for period, month in reference.months.items()}
        expected_contracts = {
            (key, str(total.reported), str(total.normalized), str(len(total.observed_months)),
             str(len(total.missing_months)), "" if total.completed_margin is None else str(total.completed_margin))
            for key, total in reference.contracts.items()
        }
        for view, fields, expected in (
            ("group_month", "posting_month, customer_group, reported, normalized", expected_groups),
            ("portfolio_month", "posting_month, reported, normalized", expected_portfolio),
            ("contract_total", "contract_id, reported, normalized, observed_count, missing_count, completed_margin", expected_contracts),
        ):
            actual = query(f"SELECT {fields} FROM watt_reporting.{view} WHERE snapshot = '{snapshot}'")
            if Counter(actual) != Counter(expected):
                raise AssertionError(f"{snapshot} {view} mismatch: {len(actual)} rows; "
                                     f"sample unexpected={sorted(set(actual) - expected)[:3]}")
        # Compare every observed contract-month, not just sums that can cancel out.
        expected_rows = {
            (row.contract_id, str(row.month), reference.groups[row.contract_id],
             str(margin(row)), str(margin(row, normalized=True)))
            for row in fixture.months if row.month <= cutoff
        }
        actual_rows = query("SELECT contract_id, posting_month, customer_group, reported, normalized "
                            f"FROM watt_reporting.contract_month WHERE snapshot = '{snapshot}'")
        assert len(actual_rows) == len(expected_rows) and set(actual_rows) == expected_rows, snapshot
        print(f"{snapshot}: {len(expected_rows):,} contract-month rows, "
              f"{len(expected_contracts):,} contracts, {len(expected_groups)} group totals, "
              f"{len(expected_portfolio)} portfolio totals match Python", flush=True)
    permissions = query("""
        SELECT n.nspname, c.relname,
               has_table_privilege(current_user, c.oid, 'SELECT'),
               has_table_privilege(current_user, c.oid, 'INSERT, UPDATE, DELETE, TRUNCATE'),
               has_schema_privilege(current_user, n.oid, 'USAGE'),
               has_schema_privilege(current_user, n.oid, 'CREATE')
        FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname IN ('watt_source', 'watt_reporting') AND c.relkind IN ('r', 'v')
    """)
    assert len(permissions) == 13, permissions
    for schema, name, select, write, usage, create in permissions:
        expected_access = "t" if schema == "watt_reporting" else "f"
        assert (select, write, usage, create) == (expected_access, "f", expected_access, "f"), name
    print("Analyst can query reporting views; source access, mutations, and reporting DDL are denied.")


if __name__ == "__main__":
    verify()
