# MacroLens

MacroLens is a personal U.S. macroeconomic analytics platform for collecting, validating, transforming, and interpreting economic data.

The project is in active development. Current macro classifications are deterministic analytical tools; MacroLens does not generate trading signals. AI interpretation is planned but not implemented yet, and full historical vintage/revision methodology remains future work.

## Pipeline

```text
FRED API
-> RAW JSON
-> Validation
-> PostgreSQL observations
-> Computed features
-> Macro modules / state
-> USA Economy Now aggregation
-> API
-> Dashboard
-> future AI interpretation
```

## Technology Stack

- Python
- PostgreSQL
- Docker
- FRED API
- pandas
- psycopg
- httpx
- PyYAML
- pytest

## Implemented

- Configurable `series.yaml`
- Generic series ingestion
- Batch ingestion
- Immutable RAW snapshots
- Observation validation
- Idempotent database writes
- `computed_features` layer
- Batch feature computation
- Labor Market Momentum v1
- Snapshots for six macro domains: Labor, Inflation, Growth, Consumer, Housing, and Financial Conditions
- USA Economy Now aggregation layer
- MacroLens API v1 for current snapshots
- Current-vintage observation and feature history endpoints for charts
- Dashboard v1 for current USA Economy Now data
- Charts v1 for interactive current-vintage history across six macro domains
- Indicator Explorer v1 for configured series and available transformations
- Macro Calendar v1 for date-level FRED releases relevant to configured indicators
- Macro Relationships v1 for descriptive current-vintage comparisons
- Automated tests

## Labor Series

- `PAYEMS`: Nonfarm Payrolls
- `UNRATE`: Unemployment Rate
- `UNEMPLOY`: Unemployment Level (unemployed persons)
- `ICSA`: Initial Jobless Claims
- `CCSA`: Continuing Jobless Claims
- `JTSJOL`: JOLTS Job Openings
- `CIVPART`: Labor Force Participation Rate
- `CES0500000003`: Average Hourly Earnings

## Local Usage

```powershell
docker compose up -d
.\.venv\Scripts\python -m app.database.init_db
.\.venv\Scripts\python -m app.database.sync_series
.\.venv\Scripts\python -m app.ingestion.ingest_all
.\.venv\Scripts\python -m app.analytics.compute_all
.\.venv\Scripts\python -m app.analytics.labor_snapshot
.\.venv\Scripts\python -m app.ingestion.sync_release_calendar
.\.venv\Scripts\python -m pytest
```

## Development API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

Interactive FastAPI docs are available at `/docs`.

API v1 exposes current macro snapshots and current-vintage historical series for
charts. Chart history uses the latest stored value for each observation date; it
does not reconstruct what was known on that date. Full historical point-in-time
API support is not implemented yet.

Available routes:

- `GET /health`
- `GET /api/v1/economy/us`
- `GET /api/v1/economy/us/state`
- `GET /api/v1/economy/us/labor`
- `GET /api/v1/economy/us/inflation`
- `GET /api/v1/economy/us/growth`
- `GET /api/v1/economy/us/consumer`
- `GET /api/v1/economy/us/housing`
- `GET /api/v1/economy/us/financial-conditions`
- `GET /api/v1/series/{series_id}/history`
- `GET /api/v1/series/{series_id}/features/{feature_name}/history`
- `GET /api/v1/series`
- `GET /api/v1/series/{series_id}`
- `GET /api/v1/series/{series_id}/features`
- `GET /api/v1/analytics/yield-curve/2s10s/history`
- `GET /api/v1/calendar?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&category=...`
- `GET /api/v1/releases/{release_id}`
- `GET /api/v1/relationships/compare?left_series=...&right_series=...&left_feature=...&right_feature=...&start_date=...&end_date=...`

History routes accept optional `start_date` and `end_date` query parameters
in `YYYY-MM-DD` format.

## Development Dashboard

Run the backend and frontend in two terminals.

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Development URLs:

- API: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Overview: `http://127.0.0.1:5173/#/`
- Macro State: `http://127.0.0.1:5173/#/state`
- Charts: `http://127.0.0.1:5173/#/charts`
- Indicators: `http://127.0.0.1:5173/#/indicators`
- Calendar: `http://127.0.0.1:5173/#/calendar`
- Relationships: `http://127.0.0.1:5173/#/relationships`

Overview shows the current macro snapshot. Charts shows curated historical macro charts. Indicators lets you browse individual configured series and their available stored transformations. Calendar shows scheduled and historical release dates from FRED for active configured MacroLens indicators. For seven known releases, the API adds the publisher's scheduled Eastern time and its UTC instant; the frontend displays that instant in Europe/Warsaw. Other releases have null time fields. Consensus, actual-at-release values, and surprises are not included.

Charts and Indicators use the latest stored values for each observation date, so revised series may differ from their original releases. Calendar detail readings use the same current-vintage context and do not represent values known at the release date. ALFRED and vintage-aware point-in-time history remain future work.

Refresh the Calendar with `python -m app.ingestion.sync_release_calendar`. The command defaults to one year of historical dates and six months ahead. Use `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` to choose another window. It fetches only releases linked to active configured series, stores each FRED response immutably under `data/raw/fred/releases`, and upserts release metadata and dates. [FRED's release-date documentation](https://fred.stlouisfed.org/docs/api/fred/release_dates.html) notes that source-published dates do not necessarily mark when data becomes available on FRED or ALFRED.

Calendar time metadata is a small, explicit API mapping based on the official [BLS schedule](https://www.bls.gov/schedule/2026/home.htm), [BEA schedule](https://www.bea.gov/news/schedule/full), and [Census construction schedule](https://www.census.gov/construction/soc/schedule.html). FRED does not provide or guarantee these times, and individual publication schedules may change. The mapping uses `America/New_York`, not a fixed UTC offset. It requires no schema migration or calendar resync; syncing still refreshes release dates.

Relationships compares two or three configured histories. Omit a feature parameter to use raw observations; a feature parameter selects an existing stored transformation. The API groups observations at the lowest selected frequency and returns the latest non-null observation within each period. It reports Pearson correlation only for periods where both series have values. Indexed mode uses 100 at the first shared nonzero period and changes display values only. See [relationship methodology](docs/methodology.md#macro-relationships-v1) for details. These comparisons describe historical co-movement, not causation or forecasts.

## Macro State v1

Macro State (`#/state`, `GET /api/v1/economy/us/state`) is a descriptive synthesis
of the existing USA Economy Now snapshot. It shows selected readings, the existing
classifications, deterministic evidence, and freshness for each of the six domains.
The existing overall labor momentum is preserved. It creates no single economic
score and does not predict recession or markets.

Cross-currents highlight conflicting directional evidence using three explicit
rules documented in [the methodology](docs/methodology.md#macro-state-v1).
They do not imply causation or forecasts. The current-vintage limitation still
applies: the state uses latest stored values, including revisions, and does not
reconstruct historical knowledge. Historical Macro State is not implemented.

## Roadmap

- Inflation
- Growth
- Consumer
- Housing
- Financial Conditions
- API/dashboard
- AI interpretation
