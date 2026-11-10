-- Run inside the loader's transaction in a dedicated Watt database.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'watt_analyst') THEN
        RAISE EXCEPTION 'watt_analyst already exists; use a fresh Watt cluster';
    END IF;
END
$$;
CREATE ROLE watt_analyst NOLOGIN;
CREATE SCHEMA watt_source;
CREATE SCHEMA watt_reporting;
REVOKE ALL ON SCHEMA watt_source, watt_reporting FROM PUBLIC;

CREATE TABLE watt_source.snapshot (
    snapshot text PRIMARY KEY,
    cutoff date NOT NULL CHECK (extract(day FROM cutoff) = 1)
);

CREATE TABLE watt_source.contract (
    contract_id text PRIMARY KEY,
    customer_id text NOT NULL,
    solar boolean,
    starts date NOT NULL CHECK (extract(day FROM starts) = 1),
    ends date NOT NULL CHECK (extract(day FROM ends) = 1 AND ends >= starts),
    plan text NOT NULL
);

CREATE TABLE watt_source.contract_month (
    contract_id text REFERENCES watt_source.contract,
    posting_month date CHECK (extract(day FROM posting_month) = 1),
    billed_days integer NOT NULL CHECK (billed_days BETWEEN 0 AND
        extract(day FROM posting_month + interval '1 month - 1 day')),
    imported_kwh integer NOT NULL CHECK (imported_kwh >= 0),
    exported_kwh integer NOT NULL CHECK (exported_kwh >= 0),
    energy_revenue bigint NOT NULL,
    fixed_fees bigint NOT NULL,
    bill_credits bigint NOT NULL,
    export_credits bigint NOT NULL,
    wholesale bigint NOT NULL,
    ancillary bigint NOT NULL,
    transmission bigint NOT NULL,
    other bigint NOT NULL,
    usage_valid boolean NOT NULL,
    PRIMARY KEY (contract_id, posting_month)
);
CREATE INDEX contract_month_period_idx ON watt_source.contract_month (posting_month);

CREATE TABLE watt_source.adjustment (
    evidence_id text PRIMARY KEY,
    contract_id text NOT NULL,
    posting_month date NOT NULL,
    service_month date NOT NULL CHECK (extract(day FROM service_month) = 1 AND service_month <= posting_month),
    cost_cents bigint NOT NULL,
    component text NOT NULL CHECK (component IN ('wholesale', 'ancillary', 'transmission', 'other')),
    FOREIGN KEY (contract_id, posting_month) REFERENCES watt_source.contract_month
);

-- Both reporting snapshots are after the same fixed winter window. Derive the
-- profile only from valid, complete customer-month observations in that window.
CREATE VIEW watt_source.winter_profile AS
WITH observations AS (
    SELECT c.customer_id, m.posting_month, max(m.imported_kwh) AS kwh,
           max(m.billed_days) AS days, bool_and(c.solar IS FALSE) AS non_solar
    FROM watt_source.contract_month m JOIN watt_source.contract c USING (contract_id)
    WHERE m.posting_month BETWEEN DATE '2024-12-01' AND DATE '2025-02-01'
    GROUP BY c.customer_id, m.posting_month
    HAVING count(*) = 1 AND bool_and(m.usage_valid AND
        m.billed_days = extract(day FROM m.posting_month + interval '1 month - 1 day'))
), rates AS (
    SELECT customer_id, sum(kwh)::numeric / sum(days) AS rate,
           bool_and(non_solar) AS non_solar
    FROM observations GROUP BY customer_id HAVING count(*) = 3
), ranked AS (
    SELECT rate, row_number() OVER (ORDER BY rate) AS rank, count(*) OVER () AS n
    FROM rates WHERE non_solar
), cutoff AS MATERIALIZED (
    -- Compute the single median once, even if the join scans it per customer.
    SELECT avg(rate) AS rate FROM ranked WHERE rank IN ((n + 1) / 2, (n + 2) / 2)
)
SELECT r.customer_id, CASE WHEN cutoff.rate IS NULL THEN NULL
    WHEN r.rate >= cutoff.rate THEN 'high_winter' ELSE 'low_winter' END AS profile
FROM rates r CROSS JOIN cutoff;

CREATE VIEW watt_reporting.snapshots AS SELECT snapshot, cutoff FROM watt_source.snapshot;

CREATE VIEW watt_reporting.contract_month AS
WITH adjustments AS (
    SELECT contract_id, posting_month, sum(cost_cents) AS all_cost,
           sum(cost_cents) FILTER (WHERE service_month = posting_month) AS current_cost
    FROM watt_source.adjustment GROUP BY contract_id, posting_month
)
SELECT s.snapshot, m.*, c.customer_id, c.plan, c.solar, w.profile AS winter_profile,
       CASE WHEN c.solar IS TRUE THEN 'solar'
            WHEN c.solar IS FALSE THEN coalesce(w.profile, 'unclassified')
            ELSE 'unclassified' END AS customer_group,
       b.margin - coalesce(a.all_cost, 0) AS reported,
       b.margin - coalesce(a.current_cost, 0) AS normalized
FROM watt_source.contract_month m
JOIN watt_source.snapshot s ON m.posting_month <= s.cutoff
JOIN watt_source.contract c USING (contract_id)
LEFT JOIN watt_source.winter_profile w USING (customer_id)
LEFT JOIN adjustments a USING (contract_id, posting_month)
CROSS JOIN LATERAL (
    SELECT m.energy_revenue - m.bill_credits - m.export_credits + m.fixed_fees
           - m.wholesale - m.ancillary - m.transmission - m.other AS margin
) b;

CREATE VIEW watt_reporting.adjustments AS
SELECT s.snapshot, a.* FROM watt_source.adjustment a
JOIN watt_source.snapshot s ON a.posting_month <= s.cutoff;

CREATE VIEW watt_reporting.group_month AS
SELECT snapshot, posting_month, customer_group, sum(reported) AS reported,
       sum(normalized) AS normalized, count(DISTINCT customer_id) AS customer_count
FROM watt_reporting.contract_month GROUP BY snapshot, posting_month, customer_group;

CREATE VIEW watt_reporting.portfolio_month AS
SELECT snapshot, posting_month, sum(reported) AS reported, sum(normalized) AS normalized
FROM watt_reporting.contract_month GROUP BY snapshot, posting_month;

CREATE VIEW watt_reporting.contract_total AS
WITH totals AS (
    SELECT snapshot, contract_id, sum(reported) AS reported, sum(normalized) AS normalized,
           count(*) AS observed_count
    FROM watt_reporting.contract_month GROUP BY snapshot, contract_id
), coverage AS (
    SELECT s.snapshot, s.cutoff, c.*,
           (extract(year FROM least(c.ends, s.cutoff)) - extract(year FROM c.starts)) * 12
           + extract(month FROM least(c.ends, s.cutoff)) - extract(month FROM c.starts) + 1 AS expected
    FROM watt_source.snapshot s JOIN watt_source.contract c ON c.starts <= s.cutoff
)
SELECT c.snapshot, c.contract_id, c.customer_id, c.starts, c.ends,
       coalesce(t.reported, 0) AS reported, coalesce(t.normalized, 0) AS normalized,
       coalesce(t.observed_count, 0) AS observed_count,
       c.expected - coalesce(t.observed_count, 0) AS missing_count,
       CASE WHEN c.ends <= c.cutoff AND t.observed_count = c.expected THEN t.reported END AS completed_margin
FROM coverage c LEFT JOIN totals t USING (snapshot, contract_id);

GRANT USAGE ON SCHEMA watt_reporting TO watt_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA watt_reporting TO watt_analyst;
