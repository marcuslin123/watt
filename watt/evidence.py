"""Retrieve dated evidence from the prepared library using narrow parameters."""
from datetime import date

from psycopg.rows import dict_row


def search_evidence(connection, snapshot, month, words="", *, group=None,
                    contract_id=None, evidence_id=None, kind=None, limit=8):
    period = date.fromisoformat(month) if isinstance(month, str) else month
    if period.day != 1:
        raise ValueError("Use the first day of the reporting month")
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("""
            WITH applicable AS (
                SELECT DISTINCT ON (e.document_key) e.*
                FROM watt_reporting.evidence e
                JOIN watt_reporting.snapshots s ON s.snapshot = %(snapshot)s
                WHERE %(month)s::date <= s.cutoff
                  AND e.published_on < s.cutoff + interval '1 month'
                  AND e.effective_from <= %(month)s::date
                  AND (e.effective_until IS NULL OR e.effective_until > %(month)s::date)
                  AND (e.customer_group IS NULL OR e.customer_group = %(group)s)
                  AND (e.contract_id IS NULL OR e.contract_id = %(contract_id)s)
                ORDER BY e.document_key, e.version DESC
            ), term AS (
                SELECT websearch_to_tsquery('english', %(words)s) AS query
            )
            SELECT evidence_id, version, kind, title, section, published_on, effective_from,
                   customer_group, contract_id, body, source_url, synthetic
            FROM applicable CROSS JOIN term
            WHERE (%(evidence_id)s::text IS NULL OR evidence_id = %(evidence_id)s)
              AND (%(kind)s::text IS NULL OR kind = %(kind)s)
              AND (%(words)s = '' OR terms @@ term.query)
            ORDER BY ts_rank(terms, term.query) DESC, evidence_id
            LIMIT %(limit)s
        """, {"snapshot": snapshot, "month": period, "group": group, "contract_id": contract_id,
               "evidence_id": evidence_id, "kind": kind, "words": words,
               "limit": max(1, min(limit, 20))})
        return cursor.fetchall()
