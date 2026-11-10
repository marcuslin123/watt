-- Public context is deliberately separate from synthetic customer evidence.
INSERT INTO watt_source.evidence (
    evidence_id, document_key, version, kind, title, section, published_on, effective_from,
    body, source_url, synthetic
) VALUES
('ercot-rtcb-go-live', 'ercot-rtcb-go-live', 1, 'market', 'ERCOT RTC+B implementation notice',
 'Market Notice M-F110525-04', '2025-12-05', '2025-12-05',
 'ERCOT confirmed its Real-Time Co-optimization Plus Batteries implementation for operating day December 5, 2025. This is market context; the notice does not link the change to any synthetic customer margin.',
 'https://www.ercot.com/services/comm/mkt_notices/M-F110525-04', false);

CREATE TABLE watt_source.weather (
    location text NOT NULL,
    month date NOT NULL,
    published_on date NOT NULL,
    mean_high_f numeric(4,1) NOT NULL,
    mean_low_f numeric(4,1) NOT NULL,
    source_url text NOT NULL,
    PRIMARY KEY (location, month)
);
-- The real December report was issued in January; it is deliberately ineligible
-- for the December-as-of snapshot, even though its measurements describe December.
INSERT INTO watt_source.weather VALUES (
    'DFW', '2025-12-01', '2026-01-01', 63.9, 42.6,
    'https://forecast.weather.gov/product.php?format=txt&glossary=0&issuedby=DFW&product=CLM&site=IWX&version=10'
);
CREATE VIEW watt_reporting.weather AS SELECT * FROM watt_source.weather;
GRANT SELECT ON watt_reporting.weather TO watt_analyst;
