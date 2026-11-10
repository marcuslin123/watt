"""Create a dedicated local login for the reporting service."""
import os

import psycopg
from psycopg import sql


def main():
    password = os.environ.get("WATT_READER_PASSWORD")
    if not password:
        raise SystemExit("Set WATT_READER_PASSWORD before provisioning")
    with psycopg.connect() as conn:
        existing = conn.execute("SELECT 1 FROM pg_roles WHERE rolname='watt_reader'").fetchone()
        if existing:
            raise SystemExit("watt_reader already exists; reuse its original password")
        conn.execute(sql.SQL("CREATE ROLE watt_reader LOGIN PASSWORD {}").format(sql.Literal(password)))
        conn.execute("GRANT watt_analyst TO watt_reader")
    print("Created watt_reader with reporting access only.")


if __name__ == "__main__":
    main()
