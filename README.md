# Watt

Watt investigates margin changes in a retail electricity portfolio. See the [product brief](docs/prd.md), [design](docs/design.md), and [progress log](PROGRESS.md).

## Generate and verify the synthetic portfolio

From the repository root, with Python 3.11 or newer:

```sh
python3 -m watt.synthetic data/generated/demo
python3 -m unittest discover -s tests -v
```

No third-party packages or credentials are needed for this milestone. The exporter requires a new destination directory to avoid overwriting an existing export. It writes a manifest, `contracts.jsonl.gz`, and `contract_months.jsonl.gz`. Every record is fictional. The manifest defines the November and December 2025 snapshot cutoffs; both use the same immutable records. Monetary fields are integer USD cents and usage is whole kWh.

The suite checks exact totals across 24 reporting months and verifies the December portfolio movement against independently specified targets. It also covers adjustment signs, incomplete contract history, duplicate rows, and winter classification cutoffs.

## Load and verify PostgreSQL

Install Docker with Compose and have `psql` on your path. Set a local database password in the shell (do not commit it). The Compose service binds only to localhost and stores data in a named volume.

```sh
read -rs WATT_DB_PASSWORD
export WATT_DB_PASSWORD
docker compose -p watt-milestone up -d --wait postgres
export PGHOST=127.0.0.1 PGPORT="${WATT_DB_PORT:-55432}" PGDATABASE=watt PGUSER=watt_owner
export PGPASSWORD="$WATT_DB_PASSWORD"
python3 -m watt.load_postgres data/generated/demo
python3 -m watt.verify_postgres
```

The one-time loader targets a fresh Watt cluster. Schema, roles, and fixture rows load in one transaction. It refuses to replace an existing installation. To reuse the seeded database after restart, skip the load step. Keep using the original password with the existing volume.

Query the `watt_reporting` views with an explicit `snapshot` filter (`initial` or `refreshed`). `watt_analyst` is a no-login role with reporting access only; the verifier uses the setup account to assume that role in a read-only transaction. Do not give an application the setup account's credentials.

## Check evidence retrieval

Fresh loads include the prepared synthetic source library. For a database loaded before the library was added, apply the one-time upgrade with `psql -X -1 -v ON_ERROR_STOP=1 -f sql/evidence.sql` using the setup account.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m watt.verify_retrieval
```

The checks query PostgreSQL as `watt_analyst`. They cover effective dates, publication cutoffs, replacement versions, exact IDs and contract scope, and an intentionally unresolved usage change. The library is synthetic and its records do not authorize actions.
