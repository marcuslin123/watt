# Watt

Watt investigates margin changes in a retail electricity portfolio. See the [product brief](docs/prd.md), [design](docs/design.md), and [progress log](PROGRESS.md).

## Generate and verify the synthetic portfolio

From the repository root, with Python 3.11 or newer:

```sh
python3 -m watt.synthetic data/generated/demo
python3 -m unittest discover -s tests -v
```

No third-party packages or credentials are needed for this milestone. The exporter requires a new destination directory to avoid overwriting an existing export. It writes a manifest, `contracts.jsonl.gz`, and `contract_months.jsonl.gz`. Every record is fictional. The manifest defines the November and December 2025 snapshot cutoffs; both use the same immutable records. Monetary fields are integer USD cents and usage is whole kWh.

The suite checks exact totals across 24 reporting months and verifies the December portfolio movement against independently specified targets. It also covers adjustment signs, incomplete contract history, duplicate rows, and winter classification cutoffs. PostgreSQL ingestion and the dashboard are later milestones.
