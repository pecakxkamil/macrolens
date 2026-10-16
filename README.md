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
- `GET /api/v1/economy/us/mci`
- `GET /api/v1/economy/us/mci/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
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
- Macro Index: `http://127.0.0.1:5173/#/macro-index`
- Charts: `http://127.0.0.1:5173/#/charts`
- Indicators: `http://127.0.0.1:5173/#/indicators`
- Calendar: `http://127.0.0.1:5173/#/calendar`
- Relationships: `http://127.0.0.1:5173/#/relationships`

Overview shows the current macro snapshot. Charts shows curated historical macro charts. Indicators lets you browse individual configured series and their available stored transformations. Calendar shows scheduled and historical release dates from FRED for active configured MacroLens indicators. For seven known releases, the API adds the publisher's scheduled Eastern time and its UTC instant; the frontend displays that instant in Europe/Warsaw. Other releases have null time fields. Consensus, actual-at-release values, and surprises are not included.

Charts and Indicators use the latest stored values for each observation date, so revised series may differ from their original releases. Calendar detail readings use the same current-vintage context and do not represent values known at the release date. The separate PIT Macro Index reconstructs only its 15 components from ALFRED vintages; these other views remain current-vintage.

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

## Macro Conditions Index v1

Macro Index (`#/macro-index`) shows a descriptive 0-100 monthly composite and
six equally weighted domain subindices. Fifteen explicit components use existing
stored feature histories. Activity components use expanding historical midrank
percentiles; inflation uses a symmetric distance-from-2% reference score.
The page exposes raw values, normalization, weights, contributions, and
freshness, alongside a historical chart and optional domain lines.

Missing inputs retain fixed weights and leave scores unavailable. Activity
scores need 60 monthly observations, or 20 quarterly GDP observations. GDP is
eligible after its quarter ends and may be carried for two additional months.
The current index identifies the latest complete month and the latest evaluated
month. Full formulas, orientations, and coverage rules are in
[the methodology](docs/methodology.md#macro-conditions-index-v1).

MCI uses current-vintage histories that include revisions. It does not recreate
historical publication availability and must not be treated as an investable or
backtest signal. It provides no market forecast, recession probability, or asset
overlay. Existing feature ingestion/computation supplies the data; no index
table, migration, or new ingestion is required.

## Roadmap

- Inflation
- Growth
- Consumer
- Housing
- Financial Conditions
- API/dashboard
- AI interpretation

## Point-in-Time Macro Conditions Index infrastructure v1

Macro Index defaults to **Point-in-time**. The selector also retains the separate
**Current-vintage** product and its existing endpoints. Point-in-time MCI is
designed to reduce look-ahead bias; it is not a validated trading or forecasting
model. ALFRED establishes availability by date, not by minute.

PIT endpoints:

- `GET /api/v1/economy/us/mci/point-in-time`
- `GET /api/v1/economy/us/mci/point-in-time/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /api/v1/economy/us/mci/point-in-time/{as_of_date}` (exact-date input audit)

Set the existing database settings and `FRED_API_KEY` in `.env`, then run from
the project root:

```powershell
.\.venv\Scripts\python.exe -m app.database.init_db
.\.venv\Scripts\python.exe -m app.ingestion.backfill_vintages
.\.venv\Scripts\python.exe -m app.analytics.point_in_time_mci
```

The schema extension marks trusted ALFRED rows separately from ordinary FRED
snapshots, stores validity interval ends, and records completed backfill coverage.
The backfill supports only PAYEMS, UNRATE, ICSA, CPIAUCSL, CPILFESL, PCEPILFE,
GDPC1, CFNAI, INDPRO, PCEC96, DSPIC96, HOUST, PERMIT, HSN1F, and NFCI.
Use repeated `--series` arguments to select a subset, or `--end-date YYYY-MM-DD`
to choose the retrieval cutoff. It downloads original-unit real-time change
intervals from the FRED/ALFRED observations API starting at `1776-07-04`.

Raw responses are immutable under `data/raw/alfred/<SERIES_ID>/`. Matching saved
pages resume interrupted runs, with at most three pages fetched concurrently.
Each series commits atomically; rerunning does not duplicate observation/vintage
keys. Conflicting values in already trusted ALFRED rows fail the transaction
instead of rewriting history. Ordinary snapshot ingestion cannot overwrite them.

The rebuild bulk-loads vintages, sweeps historical month-ends, and writes the
optional ignored artifact `data/derived/mci_point_in_time_v1.json`. History API
requests reuse it only when the completed-backfill signature and requested
coverage match. After a new backfill, rerun the rebuild; absent/stale caches
fall back to reconstruction. The exported coverage identifies the actual first
valid full-index date, missing series, and per-series vintage history.

The completed local backfill through **2026-10-09** contains **1,066,512**
trusted vintage interval rows. Its rebuilt history has **185** month-ends, with
the first valid full PIT MCI on **2011-05-31**. These are measured coverage
results for this backfill; future runs expose their own derived metadata.

See [PIT methodology](docs/methodology.md#point-in-time-macro-conditions-index-infrastructure-v1)
for feature reconstruction, carry rules, normalization, and audit semantics.

## Market Comparison Lab v1

Open `#/market-comparison` to compare overall MCI with two separately configured
market assets. Point-in-time MCI and Nasdaq are selected by default. The default
5Y window falls back to Max only when common calendar coverage is shorter; missing
MCI months remain gaps. Max begins at the first shared valid comparison date.

| FRED series | Asset | Class | Source organization | Units |
| --- | --- | --- | --- | --- |
| NASDAQCOM | Nasdaq Composite | equity_index | Nasdaq, Inc. | index points |
| CBBTCUSD | Bitcoin | cryptocurrency | Coinbase | USD |

`config/market_assets.yaml` contains the explicit universe, FRED provider, source
links, observation conventions, and attribution. Market metadata is stored in
`series` with category `market` and `active=false` to exclude it from macro
workflows. Observations reuse `observation_vintages` and its existing uniqueness
constraint. No schema migration is needed, and macro configuration, MCI inputs,
weights, features, scores, and vintage selection are unchanged.

Refresh daily market snapshots using the existing `.env` database settings and
FRED key:

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m app.ingestion.ingest_market_assets
# Optional single asset:
.\.venv\Scripts\python.exe -m app.ingestion.ingest_market_assets --asset NASDAQCOM
```

The refresh validates values, retains `.` as null, rejects incomplete snapshots,
and upserts idempotently. Original responses are stored under
`data/raw/fred/<SERIES_ID>/` using unique, exclusively created files. This is
ordinary historical market-price ingestion, not an ALFRED vintage backfill.

Read-only API:

```text
GET /api/v1/market-comparison?assets=NASDAQCOM,CBBTCUSD&start_date=2021-10-01&end_date=2026-09-30&macro_history_type=point_in_time&mode=indexed
```

Only configured assets are allowed. Defaults are `NASDAQCOM`, `point_in_time`,
and `indexed`. `mode=actual` and `macro_history_type=current_vintage` are explicit
alternatives. The response includes monthly `rows`, source `series` metadata,
common `base_date` / original `base_values`, actual market observation dates,
monthly returns, and two descriptive Pearson statistics per asset. No common
base returns `status=insufficient_overlap` with an explanation and null indexes.

Indexed mode means **MCI level + indexed assets**: MCI stays on 0-100 while assets
use a separate base-100 axis. Actual mode uses separate MCI / index-points / USD
axes. Tooltips expose prices, indexed values, macro as-of dates, and actual
market observation dates. See [market methodology](docs/methodology.md#market-comparison-lab-v1).

Run backend and frontend in separate terminals:

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

```powershell
Set-Location C:\Projects\macrolens\frontend
npm run dev
```

Inspect the page and API:

```powershell
Start-Process 'http://127.0.0.1:5173/#/market-comparison'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/market-comparison?assets=NASDAQCOM,CBBTCUSD&start_date=2021-10-01'
git status --short
git diff --stat
git diff --check
```

Market data belongs to its source organizations. FRED's official
[Nasdaq notes](https://fred.stlouisfed.org/series/NASDAQCOM) and
[Coinbase notes](https://fred.stlouisfed.org/series/CBBTCUSD) describe copyright
and permitted use; attribution does not grant redistribution rights. The API
serves monthly comparison points, not complete daily raw datasets. This lab is
a descriptive workspace, not a trading signal, forecast, backtest, or investment
recommendation. Gold and other assets are outside v1.


## Macro?Market Lead/Lag Analysis v1

The separate Lead / Lag Analysis section of `#/market-comparison` uses existing
Nasdaq Composite (`NASDAQCOM`) and Bitcoin (`CBBTCUSD`) observations only. PIT
MCI is the default; current-vintage is explicitly optional. No MCI construction,
weights, ingestion or original Market Comparison alignment is changed.

Definitions: `delta_MCI_t = MCI_t - MCI_(t-1)` in index points;
`R_asset_t = 100 * (P_t / P_(t-1) - 1)` in percent, where `P_t` is the last
finite positive observed price on or before calendar month-end. This analysis
rejects that price if it is more than **7 calendar days** old. This permits
ordinary weekends/holidays while preventing indefinite stale-price carry.
This freshness rule applies only to the new analysis.

For each integer `k = -6,...,+6`, compute
`Corr(delta_MCI_t, R_asset_(t+k))`. Positive k means MCI change precedes the
return; negative k means return precedes MCI change; zero is contemporaneous.
Pairs use exact calendar-month dictionary keys, never row-index shifts,
nearest-month matches, interpolation or multi-month returns. Missing/null MCI
at t or the immediately preceding month invalidates the change. An unavailable
price at either consecutive month-end invalidates the return. Dates and price
observation dates are included in each scatter-ready pair.

Only the MCI anchor month-end t is restricted by start_date/end_date (inclusive).
Full prior stored history is loaded for deltas, negative lags, returns and rolling
windows. Prices are loaded through up to six months after end_date, capped at
today; incomplete calendar months are excluded. Positive-lag return months may
therefore fall outside the reporting range. Missing actual observations remain
unavailable, including at the dataset boundary. The API exposes its loading
window and reporting/coverage metadata.

Pearson r uses finite valid pairs; N and first/last valid MCI anchor dates are
reported for every lag. Fewer than three pairs or zero variance returns null,
never zero. There are no p-values, optimized lags or regression forecasts.
Rolling windows cover exactly 24 or 36 calendar anchor months ending at t and
require every paired month to be valid. A missing month makes r null; windows
never compress to the last N available observations. Rolling windows can begin
before the reporting range. Positive k uses later returns relative to the
rolling anchor: these diagnostics are retrospective, not investable signals.

All 13 lags remain visible with sample counts, a rolling stability chart and
scatter tooltips identifying anchor month, return month, units and asset.
Correlation is descriptive, not causal or predictive. Same-month correlation
is not a prediction. Multiple testing and unstable correlations limit
interpretation. PIT availability is date-level, not intraday; market histories
are latest stored observations rather than vintage market histories.

Read-only endpoint: `GET /api/v1/market-comparison/lead-lag` with `assets`,
`start_date`, `end_date`, `macro_history_type=point_in_time|current_vintage`,
and `rolling_window=24|36`. Both existing assets are returned by default;
the UI requests its selected analysis asset. Asset whitelist, dates, history
mode and rolling window are validated. No schema change or data sync is needed.
