"""One-time setup for the separate local workflow-state role."""
import os
from pathlib import Path

import psycopg
from psycopg import sql


def main():
    password = os.environ.get("WATT_STATE_PASSWORD")
    if not password:
        raise SystemExit("Set WATT_STATE_PASSWORD")
    schema = Path(__file__).resolve().parents[1] / "sql" / "workflow.sql"
    with psycopg.connect() as conn:
        conn.execute(sql.SQL("CREATE ROLE watt_state LOGIN PASSWORD {}").format(sql.Literal(password)))
        conn.execute(schema.read_text(encoding="utf-8"))
    print("Created workflow schema and scoped state login")


if __name__ == "__main__":
    main()
