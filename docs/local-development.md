# Local development

This guide separates running the code from recreating an authorized, populated
instance. It does not grant permission to activate background data imports.

## Requirements

- Python 3.12 (the GitHub Actions version), Node.js 22 and npm.
- Docker Desktop/Engine with Compose; the development service uses PostgreSQL 17.
- A personal FRED API key for real FRED ingestion. Unit tests need no key.
- Run Python commands from the repository root so `.env` and local data paths resolve.

## Install and configure

Create a virtual environment and install `requirements.txt`. The three libraries
covered by F1 authorization must be exactly `httpx==0.28.1`,
`psycopg[binary]==3.2.13` and `pypdf==6.21.2`; install those explicit versions
after requirements. Install the frontend with `npm ci` and its committed lockfile.

PowerShell commands are in the root README. On Linux/macOS:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install httpx==0.28.1 'psycopg[binary]==3.2.13' pypdf==6.21.2
cp .env.example .env
# Edit .env before continuing.
docker compose up -d postgres
.venv/bin/python -m app.database.init_db
.venv/bin/python -m app.database.sync_series
```

The PostgreSQL Compose defaults match `.env.example`; they are local development
placeholders. Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` and
`FRED_API_KEY` in your ignored `.env`. Optional `FMP_API_KEY` is not needed for
the core walkthrough and does not activate market-cap ingestion. Never put
provider keys in `VITE_*`: those variables are exposed to the browser.

**Development exposure:** the current Compose mapping `5432:5432` publishes
PostgreSQL on all host interfaces unless restricted by the host firewall.
`macrolens_dev` is a public development placeholder, not a production secret.
Do not use this setup on an untrusted network or public server. A separate
hardening change should bind `127.0.0.1:5432:5432`, introduce a deliberately
configured password and document fresh-volume setup. Editing an environment
variable does not rotate the password of an existing PostgreSQL volume; never
recreate or delete a populated volume to apply documentation changes.

Compose creates a persistent development volume. If you already have a service
named `macrolens_postgres` or a database on port 5432, inspect/reuse the intended
development service or configure a separate one; do not replace an existing
populated instance. This guide assumes a fresh environment. It has not been
presented as a clean-room reconstruction of the full screenshot dataset.

## Small interactive walkthrough

After schema/catalog initialization, explicitly fetch one configured series:

```powershell
.venv\Scripts\python.exe -m app.ingestion.ingest_series UNRATE
.venv\Scripts\python.exe -m app.analytics.compute_features UNRATE
```

On Unix use `.venv/bin/python` instead. These commands make real provider
requests and write to your development database and ignored RAW directory.
They do not create a complete macro/earnings/forecast dataset. Start API and
Vite as documented in README and open:

`http://127.0.0.1:5173/#/explore/indicators/UNRATE`

Inspect stored observations, periods and units. Other cards can be unavailable
until their data is present. A visible Overview/Calendar can request the existing
macro refresh lifecycle; keep provider limits and your intended development
scope in mind. Missing data is not filled with zero or invented demo values.

For broader current-vintage development data, the existing explicit commands are
`python -m app.ingestion.ingest_all`, `python -m app.analytics.compute_all`
and `python -m app.ingestion.sync_release_calendar`. They involve more requests
and writes, can take time, and do not establish publisher-period evidence or
production authorizations by themselves. PIT/ALFRED backfills are separate,
potentially substantial operations; consult the methodology before running them.

## What a fresh checkout cannot provide

The repository contains the core schema, source adapters, code and tests. It
does not contain the normal database, immutable local captures, saved publication
snapshots or activation tokens. `init_db` installs the core schema; it does not
replay the reviewed Earnings/F1 activation chain. Worker activation also binds
to a specific PostgreSQL identity, schema, references, source bytes, dependency
versions and restored backup evidence. A token from another machine is invalid.

Consequently, full populated Overview, historical official document comparisons,
Earnings coverage, frozen forecasts and activated workers require separately
reviewed initialization or a securely restored authorized instance. Do not run
authorization APPLY scripts against a fresh database as a shortcut. Status APIs
may show `awaiting_activation`, while endpoints requiring absent stores can be
unavailable. This is an explicit setup boundary, not a claim of a turnkey demo.

The minimal no-secret demonstration is the screenshot walkthrough plus the
offline test suites. A portable seeded demo dataset is proposed future work;
it is not implemented or silently substituted for provider data.

## Runtime and checks

| Service | Address |
|---|---|
| UI | `http://127.0.0.1:5173/` |
| FastAPI OpenAPI | `http://127.0.0.1:8000/docs` |
| Health | `GET /health` on port 8000 |
| Series catalog | `GET /api/v1/series` |
| Calendar readings | `GET /api/v1/calendar?include_readings=true` |
| F1 state | `GET /api/v1/forecasts/status` |
| Earnings monitor state | `GET /api/v1/earnings/monitor/status` |

Run API/Vite in separate terminals. `--reload` is for development. An HTTP 200
status response can describe an inactive worker; inspect `activated` and source
check states rather than treating the response code as proof of fresh data.

If PostgreSQL is unavailable, check Docker Engine, the existing service and
credentials. If an API port is occupied, identify its process before starting
another instance. If data is missing, inspect the observation period, source
check and publication evidence; refreshing metadata alone does not prove a new
observation was fetched. If byte integrity fails, inspect checkout EOL rules
and pinned libraries; never regenerate an approval baseline just to pass CI.

## Validation without real providers

Use `python -m pytest -q` from the root and `npm test` in `frontend`.
The guards in `tests/conftest.py` and `.github/ci/no-network.cjs` reject accidental
external access. The full PostgreSQL integration sequence is specified in
`.github/workflows/ci.yml` and creates disposable test databases. It is not a
command to run against an existing personal database. Integrity checking needs
only the three pinned libraries, checkout bytes and the static V6 map.
