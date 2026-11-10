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

## Run the portfolio workspace

After loading PostgreSQL and installing the Python requirements, create the reporting login once using the setup connection from the database section. Use a separate password. For the connection URL below, use a URL-safe password (for example, a random hex string).

```sh
read -rs WATT_READER_PASSWORD
export WATT_READER_PASSWORD
.venv/bin/python -m watt.provision_reader
export WATT_READER_DSN="postgresql://watt_reader:${WATT_READER_PASSWORD}@127.0.0.1:${WATT_DB_PORT:-55432}/watt"
npm --prefix web ci
```

Run these in separate terminals (export `WATT_READER_DSN` in the API terminal):

```sh
.venv/bin/python -m uvicorn watt.api:app --host 127.0.0.1 --port 8000
npm --prefix web run dev -- --hostname 127.0.0.1
```

Open [the local workspace](http://127.0.0.1:3000). The API runs with the reporting login, never the setup account. If the login already exists, reuse its original password and skip provisioning.

To verify the browser flow with the API and frontend launched by Playwright (with `WATT_READER_DSN` set):

```sh
(cd web && npx playwright install chromium)
npm --prefix web run test:e2e
npm --prefix web run typecheck
npm --prefix web run build
```

The [portfolio](docs/evidence/portfolio.png) and [contract](docs/evidence/contract.png) captures show the live synthetic December reporting snapshot. The assertions separately verify API totals, snapshot switching, the margin basis, contract drill-down, and adjustment visibility.

## Run the local investigator

With the setup PostgreSQL connection still exported, provision a separate state login once. Use a fresh URL-safe password and keep it outside the repository.

```sh
read -rs WATT_STATE_PASSWORD
export WATT_STATE_PASSWORD
.venv/bin/python -m watt.provision_state
export WATT_STATE_DSN="postgresql://watt_state:${WATT_STATE_PASSWORD}@127.0.0.1:${WATT_DB_PORT:-55432}/watt"
```

Use `codex login status` to confirm ChatGPT sign-in, or sign in with `codex login`. Watt’s runtime checks for ChatGPT authentication and does not fall back to API-key billing. Export `WATT_READER_DSN` and `WATT_STATE_DSN` in both the API and worker terminals. Start the API and web app as above and run `.venv/bin/python -m watt.worker` in a third terminal. Refresh the portfolio and choose **Investigate** on a flagged group. The run URL can be reopened after a reload. Only Watt's scoped tools are admitted by the Codex inventory gate; the child process cannot access the workflow-state credential.

```sh
.venv/bin/python -m watt.verify_agent
WATT_RUN_LIVE=1 npm --prefix web run test:e2e
```

The browser suite’s live investigation case requires the worker to be running. It verifies live progress, the three synthetic drivers, evidence inspection, analyst review, and scenario comparison; see the [investigation capture](docs/evidence/investigation.png) and [retention comparison](docs/evidence/retention.png).

For the synthetic walkthrough, attach a dated record to contract `contract-00000` in the unresolved December Solar finding. The browser test uses December 15 and the illustrative note “This example record states that service ended on December 15.” The app labels it analyst supplied, keeps the original run, and does not infer that all affected customers moved out. Ask “Did they move out?” to inspect the unresolved finding, then compare the default retention inputs and change the with-offer probability from 80% to 70%.
