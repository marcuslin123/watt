-- Prepared synthetic documents. Run once, in the seed transaction or via psql -1.
CREATE TABLE watt_source.evidence (
    evidence_id text PRIMARY KEY,
    document_key text NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    kind text NOT NULL,
    title text NOT NULL,
    section text NOT NULL,
    published_on date NOT NULL,
    effective_from date NOT NULL,
    effective_until date CHECK (effective_until > effective_from),
    customer_group text,
    contract_id text REFERENCES watt_source.contract,
    body text NOT NULL,
    source_url text,
    synthetic boolean NOT NULL,
    terms tsvector GENERATED ALWAYS AS
        (to_tsvector('english', title || ' ' || section || ' ' || body)) STORED,
    UNIQUE (document_key, version)
);
CREATE INDEX evidence_terms_idx ON watt_source.evidence USING gin (terms);

INSERT INTO watt_source.evidence (
    evidence_id, document_key, version, kind, title, section, published_on, effective_from,
    customer_group, contract_id, body, synthetic
) VALUES
('solar-plan-v1', 'solar-plan', 1, 'plan', 'Solar export credit schedule', 'Credits §2',
 '2025-08-01', '2025-09-01', 'solar', NULL,
 'The synthetic Solar Export Credit plan adds introductory monthly credits of $5 in September, $15 in October, and $25 in November per eligible contract, in addition to its base export credit.', true),
('solar-plan-v2', 'solar-plan', 2, 'plan', 'Solar export credit schedule', 'Credits §2',
 '2025-11-20', '2025-12-01', 'solar', NULL,
 'For December, the synthetic Solar Export Credit plan adds $45 per eligible contract, up from $25 in November. The 60 eligible contracts incur $1,200 more in export credits, separate from settlement adjustments.', true),
('solar-plan-future', 'solar-plan', 3, 'plan', 'Solar export credit schedule', 'Credits §2',
 '2026-01-05', '2025-12-01', 'solar', NULL,
 'Synthetic later revision, not available at the December reporting cutoff. Never use for the historical December investigation.', true),
('solar-settlement-dec', 'solar-settlement-dec', 1, 'settlement', 'December ancillary service settlement', 'Posting note',
 '2025-12-28', '2025-12-01', 'solar', NULL,
 'A synthetic $900 ancillary service settlement for November service posted in December. Twenty separate adjustment records total $900. This is a prior-period cost, not a recurring December rate change.', true),
('service-review-00001', 'service-review-00001', 1, 'account', 'Account review note', 'Service record',
 '2025-12-29', '2025-12-01', 'solar', 'contract-00001',
 'A synthetic meter reading was validated for this service account. The account review does not establish why recorded usage changed.', true);

CREATE VIEW watt_reporting.evidence AS SELECT * FROM watt_source.evidence;
GRANT SELECT ON watt_reporting.evidence TO watt_analyst;
