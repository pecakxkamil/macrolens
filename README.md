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
-> future API / dashboard / AI interpretation
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
- Labor Market Snapshot
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

## Roadmap

- Inflation
- Growth
- Consumer
- Housing
- Financial Conditions
- USA Economy Now
- API/dashboard
- AI interpretation
