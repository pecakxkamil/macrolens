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
- Automated tests

## Labor Series

- `PAYEMS`: Nonfarm Payrolls
- `UNRATE`: Unemployment Rate
- `ICSA`: Initial Jobless Claims
- `CCSA`: Continuing Jobless Claims
- `JTSJOL`: JOLTS Job Openings
- `CIVPART`: Labor Force Participation Rate
- `CES0500000003`: Average Hourly Earnings

## Local Usage

```powershell
docker compose up -d
.\.venv\Scripts\python -m app.database.sync_series
.\.venv\Scripts\python -m app.ingestion.ingest_all
.\.venv\Scripts\python -m app.analytics.compute_all
.\.venv\Scripts\python -m app.analytics.labor_snapshot
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
- `GET /api/v1/economy/us/labor`
- `GET /api/v1/economy/us/inflation`
- `GET /api/v1/economy/us/growth`
- `GET /api/v1/economy/us/consumer`
- `GET /api/v1/economy/us/housing`
- `GET /api/v1/economy/us/financial-conditions`
- `GET /api/v1/series/{series_id}/history`
- `GET /api/v1/series/{series_id}/features/{feature_name}/history`

Both history routes accept optional `start_date` and `end_date` query parameters
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
- Dashboard: `http://127.0.0.1:5173` or the URL printed by Vite

Dashboard v1 shows current-state data only. Full historical point-in-time dashboard support is not implemented yet.

## Roadmap

- Inflation
- Growth
- Consumer
- Housing
- Financial Conditions
- API/dashboard
- AI interpretation
