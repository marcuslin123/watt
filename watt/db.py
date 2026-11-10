"""Database connection boundaries."""
from contextlib import contextmanager
import os

from fastapi import HTTPException
import psycopg
from psycopg.rows import dict_row

@contextmanager
def reporting():
    dsn = os.environ.get("WATT_READER_DSN")
    if not dsn:
        raise HTTPException(503, "Set WATT_READER_DSN for the reporting database")
    try:
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=4,
                             options="-c default_transaction_read_only=on -c statement_timeout=10000") as conn:
            yield conn
    except psycopg.Error as exc:
        raise HTTPException(503, "Reporting database unavailable") from exc
