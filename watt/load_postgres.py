"""Load the generated Watt export into a fresh PostgreSQL database via psql."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryFile

CONTRACT_FIELDS = ("contract_id", "customer_id", "solar", "starts", "ends", "plan")
MONTH_FIELDS = (
    "contract_id", "posting_month", "billed_days", "imported_kwh", "exported_kwh",
    "energy_revenue", "fixed_fees", "bill_credits", "export_credits",
    "wholesale", "ancillary", "transmission", "other", "usage_valid",
)
SNAPSHOTS = {"initial": "2025-11-01", "refreshed": "2025-12-01"}


def records(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        yield from map(json.loads, stream)


def copy_rows(stream, table, fields, rows):
    stream.write(f"COPY watt_source.{table} ({', '.join(fields)}) FROM STDIN WITH (FORMAT csv);\n")
    # CSV's unquoted empty field is PostgreSQL's default NULL marker.
    # None appears only in the nullable solar designation.
    writer = csv.writer(stream, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    stream.write("\\.\n")


def load(directory: Path) -> None:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("synthetic") is not True or manifest.get("snapshots") != SNAPSHOTS
            or manifest.get("currency") != "USD" or manifest.get("money_unit") != "cent"
            or manifest.get("contract_count") != 10_000 or manifest.get("contract_month_count") != 240_000):
        raise ValueError("Expected the Watt synthetic export manifest")

    adjustments = []

    def months():
        for row in records(directory / "contract_months.jsonl.gz"):
            adjustments.extend(
                (adj["evidence_id"], row["contract_id"], row["month"],
                 adj["service_month"], adj["cost_cents"], adj["component"])
                for adj in row["adjustments"]
            )
            yield tuple(row["month" if key == "posting_month" else key] for key in MONTH_FIELDS)

    schema = Path(__file__).resolve().parents[1] / "sql" / "postgres.sql"
    with TemporaryFile(mode="w+", encoding="utf-8", newline="") as stream:
        stream.write("BEGIN;\n")
        stream.write(schema.read_text(encoding="utf-8"))
        copy_rows(stream, "snapshot", ("snapshot", "cutoff"), SNAPSHOTS.items())
        copy_rows(stream, "contract", CONTRACT_FIELDS,
                  (tuple(row[key] for key in CONTRACT_FIELDS)
                   for row in records(directory / "contracts.jsonl.gz")))
        copy_rows(stream, "contract_month", MONTH_FIELDS, months())
        copy_rows(stream, "adjustment",
                  ("evidence_id", "contract_id", "posting_month", "service_month", "cost_cents", "component"),
                  adjustments)
        stream.write("""
DO $$
BEGIN
    IF (SELECT count(*) FROM watt_source.contract) <> 10000
       OR (SELECT count(*) FROM watt_source.contract_month) <> 240000
       OR EXISTS (
           SELECT 1 FROM watt_source.contract_month m JOIN watt_source.contract c USING (contract_id)
           WHERE m.posting_month NOT BETWEEN c.starts AND c.ends
              OR m.posting_month NOT BETWEEN DATE '2024-01-01' AND DATE '2025-12-01'
       )
       OR EXISTS (
           SELECT 1 FROM watt_source.adjustment a JOIN watt_source.contract c USING (contract_id)
           WHERE a.service_month < c.starts
       ) THEN
        RAISE EXCEPTION 'Invalid Watt synthetic fixture';
    END IF;
END
$$;
ANALYZE watt_source.contract;
ANALYZE watt_source.contract_month;
ANALYZE watt_source.adjustment;
""")
        # Seed the evidence library in the same transaction.
        stream.write(schema.with_name("evidence.sql").read_text(encoding="utf-8"))
        stream.write(schema.with_name("context.sql").read_text(encoding="utf-8"))
        stream.write("COMMIT;\n")
        stream.flush()
        stream.seek(0)
        subprocess.run(["psql", "-X", "-v", "ON_ERROR_STOP=1"], stdin=stream, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory produced by watt.synthetic")
    load(parser.parse_args().directory)
