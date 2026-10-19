# MacroLens

MacroLens collects and validates US macroeconomic data, turns observations into readable indicators, and explains them through a dashboard, a downloadable report and documented historical research.

This portfolio project demonstrates a reproducible data pipeline, SQL storage, time-series transformations, data-quality checks and communication of analytical limitations. It uses deterministic rules; it does not provide economic forecasts or trading recommendations.

## Product walkthrough

The application has three main sections, designed for a short demonstration:

| Section | What to inspect | Route |
| --- | --- | --- |
| **Overview** | Six compact domains with latest, previous and three-period readings, dated numerical changes, source links, upcoming releases and a Markdown report | `#/` |
| **Explore Data** | Select a domain and indicator, inspect its history and available transformations, change the date range, and check units, definitions and sources. Switch to existing curated chart sets when useful. | `#/explore/indicators`, `#/explore/charts` |
| **Research** | Switch between Macro Conditions Index, Macro-Market Analysis, and Indicator Relationships. Inspect their separate methods, samples, missing data and limitations. | `#/research/mci`, `#/research/macro-market`, `#/research/relationships` |

Overview prioritizes 17 current-vintage comparison rows and an official Fed target-range block across six domains. Each reading shows the latest available period, its previous period and three periods earlier, with the same transformation and units throughout. Earlier values and dates are visible immediately. Numerical arrows and differences use an explicit presentation configuration; they do not create an economy classification. Explore Data retains the broader series catalog, history, transformations, definitions and sources. Existing backend Macro State classifications remain available through the API and in the report's audit appendix.

**View full calendar** opens `#/overview/calendar` as an auxiliary view. Overview retains a seven-day preview and groups repeated low-importance releases without discarding their dates. Known release times use official publisher conventions and timezone-aware Europe/Warsaw conversion; unknown times remain explicit.

MCI is an **experimental descriptive index**, available in Research. Its 50-point reference is not a validated recession or economic-health threshold. Macro-Market Analysis combines the existing market comparison and lead/lag analysis; its correlations depend on the selected asset, dates and method. Indicator Relationships retains its separate synchronization rules.

The UI defaults to English and retains the existing optional EN/PL switch and saved preference. Technical identifiers and API contracts remain English.

### Curated Overview and report

Each domain has at most three main elements. Inflation shows CPI, core CPI and core PCE **MoM**, with smaller same-month YoY context. Industrial production, real consumption, real disposable income and **nominal** retail sales also use **MoM** with YoY context. GDP remains QoQ annualized. Financial Conditions contains the official **Fed target range**, the **10Y minus 2Y** spread and NFCI. DFF remains in Explore Data and existing analytics. Additional series remain in Explore Data, including unemployment level, saving rate, continuing claims, openings/participation/wages, headline PCE/ECI, capacity/durable goods, new home sales and other yields. No observation, feature, classification or MCI input was removed or changed.

- Monthly readings compare the exact previous calendar month and three months earlier; quarterly readings compare one and three calendar quarters earlier; weekly readings compare one and three calendar weeks earlier.
- Daily readings compare the previous available observation and three available observations earlier, with exact dates. These are not calendar-day offsets. Missing/nonfinite daily values are not counted as available observations.
- Each reading anchors to its own latest finite stored observation, regardless of the page date. Missing required calendar periods remain missing; gaps are not compressed, interpolated or replaced with a different transformation. Zero remains zero.
- Percentage rates/growth use percentage-point differences, index levels use index points and other levels retain their units. A row's shared unit applies to its three values and same-unit change; percentage-point changes remain explicitly labeled to distinguish them from percentage values. The report spells out difference units. The curve uses only synchronized same-date 10Y minus 2Y yields.
- Arrows always indicate numerical direction. Unemployment/claims increases are red and decreases green; employment, real activity/spending increases are green and decreases red. Inflation direction is neutral for both increases and decreases; lower MoM alone is not a new favorable classification. Fed/mortgage rates, Treasury spreads, nominal retail sales and NFCI changes remain neutral. These colors are presentation choices, not backend classifications or trading signals; direction and differences remain readable without color.

The existing `/api/v1/economy/us/brief` response adds `reading_comparisons`, containing all 17 current/previous/three-period comparisons plus same-date YoY contexts and their expected dates, source measure, units and computation metadata. A single shared query selects current-vintage features in the same `as_of_date/computed_at/id` order as existing histories. The database bounds returned records to the required calendar windows or four available daily observations, plus a newer missing-period marker if present. The existing six-comparison `changes` field is retained using the matched YoY contexts where needed, without a second history query. YoY is joined to the exact primary month and series, never substituted from another period. No endpoints, schema, ingestion or Research calculations were added or changed. Overview makes one aggregate request and does not load PIT history.

The compact cards show no domain assessments, per-indicator methodology blocks, raw identifiers, repeated comparison lists, cross-currents or MCI panel. Indicator names link to Explore Data, and small source links open the publisher series definition. Calendar/FOMC remain below the cards. The single Markdown export uses the **same prepared comparison objects**, values, periods and numerical changes as the screen. Technical reading/assessment evidence, precise inputs, source identifiers, timestamps and limitations remain later in its audit appendix. It does not label prior current-vintage values as original release-time readings.

### Monthly measures and official Fed target bounds

All seven MoM sources were verified against official FRED series metadata. CPIAUCSL, CPILFESL, PCEPILFE, INDPRO and RSAFS are monthly **Seasonally Adjusted** series; PCEC96 and DSPIC96 are monthly **Seasonally Adjusted Annual Rate** levels. The existing stored v1 MoM formula is reused directly, not derived from YoY or annualized again. YoY context uses the same series and exact observation month (including the seasonally adjusted CPI index, which can differ from unadjusted headline annual inflation). A missing same-month YoY is shown as missing. Original metadata responses, URLs and retrieval timestamps were archived under ignored `data/raw/fred_metadata/` during verification.

| Main MoM source | Metadata/source |
| --- | --- |
| CPI | [CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) |
| Core CPI | [CPILFESL](https://fred.stlouisfed.org/series/CPILFESL) |
| Core PCE | [PCEPILFE](https://fred.stlouisfed.org/series/PCEPILFE) |
| Industrial production | [INDPRO](https://fred.stlouisfed.org/series/INDPRO) |
| Real consumption | [PCEC96](https://fred.stlouisfed.org/series/PCEC96) |
| Real disposable income | [DSPIC96](https://fred.stlouisfed.org/series/DSPIC96) |
| Nominal retail sales | [RSAFS](https://fred.stlouisfed.org/series/RSAFS) |

The Fed block uses [DFEDTARL](https://fred.stlouisfed.org/series/DFEDTARL) and [DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU), official Board of Governors target bounds distributed by FRED: percent, daily seven-day, not seasonally adjusted. Both were verified as available before integration. They are configured only as ordinary series/level transformations, **not MCI components**. No range is inferred from DFF or futures.

Refresh only the two bounds using existing infrastructure:

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m app.database.sync_series DFEDTARL DFEDTARU
.\.venv\Scripts\python.exe -m app.ingestion.ingest_series DFEDTARL
.\.venv\Scripts\python.exe -m app.ingestion.ingest_series DFEDTARU
```

No migration, full-series batch ingestion or ALFRED backfill is required. Registration without arguments still synchronizes the configured catalog. Target raw histories remain in the existing observation-vintage tables and immutable FRED raw files. The block reads these stored observations; it does not require computed level features or make external requests during rendering. A server-side cursor consumes paired history only until the latest continuous range change or a gap is reached.

Both bounds must have a common observation date and satisfy lower <= upper. The panel shows **Observed through** and the conservative **Retrieved** date of the two source rows, separately from **Effective since**. Retrieval timestamps use the project's UTC database convention and are displayed by Poland local date. Unmatched source endpoints remain in report provenance; no age threshold or current-through-today guarantee is invented. Invalid/missing paired bounds show unavailable values without a DFF fallback.

**Last rate change** is the first observed transition into the current continuous daily range, with each bound's change in basis points. Its effective date requires a valid adjacent earlier pair. Unchanged daily observations do not establish a new FOMC decision date. Missing history or a gap leaves the effective/change fields unknown; unequal lower/upper moves are reported separately. The UI and Markdown share the same prepared range, dates and changes. FedWatch remains link-only.

The seven required MoM/YoY feature histories were already stored during this refinement; no macro ingestion or feature rebuild was needed. If an existing configured transformation is absent on another checkout, use the existing `python -m app.analytics.compute_features SERIES_ID` path for that series rather than implementing another formula. Stored monthly macro history may lag source releases; the displayed periods and report computation dates remain authoritative for the local data.

### Official FOMC schedule and optional data

Overview shows the next stored FOMC decision independently of the seven-day macro preview. The auxiliary calendar also includes these decisions under Financial Conditions, with high importance, a separate `event_id` and **no FRED release ID or mapped indicator**.

Refresh explicitly from the repository root (no API key or database migration):

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m app.ingestion.sync_fomc_calendar
```

The command reads the [Federal Reserve meeting calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), keeps current-year and published future-year meetings, and selects the final meeting day. It verifies future decision times against the [official monthly calendars](https://www.federalreserve.gov/newsevents/2026-october.htm), matching **FOMC Meeting**, rather than minutes or press conferences. Only an explicit matching time is stored; otherwise time is null. Eastern times use `America/New_York`, with standard timezone conversion to UTC and Europe/Warsaw. The [Fed's research documentation](https://www.federalreserve.gov/econres/feds/files/2021074pap.pdf) describes the Eastern-time convention. Dates/times may change, and future-year meetings are tentative until confirmed by the Fed.

Immutable source HTML and URL/retrieval/status metadata are retained in ignored `data/raw/federal_reserve/fomc/`. The normalized schedule is atomically replaced at ignored `data/derived/fomc_calendar_v1.json`; repeated refreshes do not duplicate events. Failed schedule downloads/parsing preserve the last successful snapshot. A missing monthly page leaves its time unknown. The API only reads this file; page loads never refresh external sources. A new checkout needs the explicit refresh. Missing, unreadable or exhausted schedules produce an unavailable next-decision message without blocking the macro brief. Retrieval dates remain visible; there is no invented age threshold or guarantee that the saved schedule is current. Re-run the command to check updates. Existing FRED release sync remains separate.

**CME FedWatch: link-only variant.** No authorized CME API subscription/credentials or display/export entitlement is configured. The UI/report link to [CME FedWatch](https://www.cmegroup.com/fedwatch), explicitly state that probabilities are not integrated, and contain no probability snapshots, histories or official target-range estimate. The effective federal funds reading remains a distinct observed rate. A future data integration would require authorized [official FedWatch API](https://www.cmegroup.com/market-data/market-data-api/fedwatch-api.html) access, EOD data and history for the same meeting, and confirmation of rights for display, local retention and Markdown export. No account, subscription, scraping substitute or probability engine was added. See [CME's methodology](https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html).

**PMI: omitted.** No authorized ISM or S&P dataset/feed is configured. ISM's [report terms and historical-data access](https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/september/) require appropriate permission; public reports alone do not establish embedding/export rights. [FRED removed ISM series at the provider's request](https://news.research.stlouisfed.org/2016/06/institute-for-supply-management-data-to-be-removed-from-fred/), so legacy identifiers are not a viable fallback. [S&P Global's PMI FAQ](https://www.spglobal.com/market-intelligence/en/solutions/products/resources/pmi-faq) describes subscription data/history. No PMI placeholders, manual readings or additional MCI components were added. The report explains the omission and does not reproduce licensed CME/PMI data.

Manual review: open Overview at 1366 px and a narrow width, inspect the 17 current/previous/three-period readings, their seven same-month YoY contexts and the Fed target block and their dates; follow a reading into Explore Data; download the Markdown and compare its main readings, dates and differences with the screen. Technical classification inputs remain in the audit appendix. Check the next FOMC decision, its provenance and Warsaw time; open the full calendar on the decision week. For example the official October 28, 2026 decision is at 19:00 PL during the US/Poland DST mismatch. Switch EN/PL and check the same data, existing three-tab navigation and Research routes. Check missing schedule behavior on a checkout without the ignored schedule file; do not delete existing source data to demonstrate it.

### Existing links remain usable

| Previous route | Destination |
| --- | --- |
| `#/state` | `#/` (combined Overview) |
| `#/charts` | `#/explore/charts` |
| `#/indicators` or `#/indicators/UNRATE` | `#/explore/indicators` or `#/explore/indicators/UNRATE` |
| `#/macro-index` | `#/research/mci` |
| `#/market-comparison` | `#/research/macro-market` |
| `#/relationships` | `#/research/relationships` |
| `#/calendar` | `#/overview/calendar` |

Legacy hashes are replaced in place, so browser history does not gain a redundant redirect entry. Backend endpoints are preserved.

## Data and pipeline

```text
FRED responses -> immutable raw files -> validation -> PostgreSQL observation vintages
    -> current-vintage features -> six domain snapshots -> Macro State -> report audit details
Current-vintage features -> bounded 18-reading comparisons -> Overview/report
ALFRED real-time intervals -> separate trusted vintage backfill -> PIT reconstruction -> PIT MCI/cache
Stored macro + Nasdaq/Bitcoin observations -> separate historical comparison analyses
FRED release metadata/dates + supported publisher time metadata -> stored calendar
Official Fed meeting/monthly calendars -> raw HTML + local schedule snapshot -> calendar/next FOMC
```

- Macro series, frequencies and units are configured in [config/series.yaml](config/series.yaml). Examples include payrolls, unemployment, CPI/PCE, GDP, consumption, housing, Treasury yields and NFCI.
- Market research uses only the existing Nasdaq Composite (`NASDAQCOM`) and Bitcoin (`CBBTCUSD`) universe in [config/market_assets.yaml](config/market_assets.yaml). FRED distributes the respective Nasdaq and Coinbase series; source conventions and attribution are exposed in the UI.
- Raw FRED/ALFRED responses are retained under `data/raw`. PostgreSQL stores series metadata, observation vintages, computed features and release-calendar records.
- Python, pandas, psycopg, HTTPX and YAML support ingestion and analytics. FastAPI exposes read-only data endpoints. React, TypeScript, Vite and Recharts render the frontend. Docker Compose provides local PostgreSQL 17.

See [architecture](docs/architecture.md), [data dictionary](docs/data-dictionary.md), [database design](docs/database-design.md) and [methodology](docs/methodology.md) for implementation details.

### Data-quality decisions

- Validation checks observation structure, dates and values before persistence. FRED `.` values remain missing, never zero.
- Observation/vintage uniqueness and idempotent upserts prevent duplicate observations on repeated runs. Raw source responses are retained for inspection.
- Source units and transformations determine presentation; numerical scale alone does not establish unit compatibility.
- Missing components and gaps stay visible. MCI is not interpolated or silently reweighted.
- Observation periods, publication dates, vintage dates and retrieval/computation times have different meanings. Snapshot dates are not verified publication dates.
- Classifications refer to their actual inputs. For example, inflation momentum compares annualized three-month growth with YoY growth; GDP momentum compares the same quarter's annualized growth with YoY growth. Neither is a comparison of successive displayed growth readings.
- Correlation modules expose pair counts, dates and their own alignment rules. Historical association does not imply causation or prediction.

### Current-vintage versus point-in-time

**Current-vintage** charts and domain snapshots use the latest stored revised observations/features. They show today's stored view of historical periods, not what was originally known on each release date. Overview and its report remain current-vintage; PIT MCI remains in Research.

**PIT MCI** reconstructs only its existing 15 component series from trusted ALFRED real-time intervals known by each historical month-end. Derived features and normalization references use those reconstructed observations. GDP becomes available at its real-time date rather than at the end of its observation quarter. Availability is date-level, not intraday. Current-vintage computed features are not substituted into PIT calculations.

PIT coverage and the earliest complete score are derived from actual stored source history; no first-valid date is hardcoded. The cache is reused only with matching backfill metadata and coverage. Rebuild it after refreshing vintages. This does not make all application history point-in-time or market history vintage-aware.

## Local setup (PowerShell)

Prerequisites: Python, Node.js/npm, Docker with Compose, and a FRED API key. Run from the project root. If the virtual environment already exists, reuse it.

```powershell
Set-Location C:\Projects\macrolens
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `FRED_API_KEY` and the `DB_*` settings in `.env`. The example database settings match Docker Compose. Keep credentials out of Git. Create `.env` only on first setup; preserve existing settings when continuing work.

Initialize and populate the existing schema and current-vintage data:

```powershell
docker compose up -d
.\.venv\Scripts\python.exe -m app.database.init_db
.\.venv\Scripts\python.exe -m app.database.sync_series
.\.venv\Scripts\python.exe -m app.ingestion.ingest_all
.\.venv\Scripts\python.exe -m app.analytics.compute_all
.\.venv\Scripts\python.exe -m app.ingestion.sync_release_calendar
.\.venv\Scripts\python.exe -m app.ingestion.ingest_market_assets
```

The presentation refactor requires no schema change. Calendar sync defaults to a year of history and six months ahead; `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` selects another interval. Market ingestion supports `--asset NASDAQCOM` or `--asset CBBTCUSD`.

Populate/rebuild PIT MCI separately when needed (the full ALFRED backfill can be substantial):

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.backfill_vintages
.\.venv\Scripts\python.exe -m app.analytics.point_in_time_mci
```

Backfill supports repeated `--series` arguments for the existing MCI universe and `--end-date YYYY-MM-DD`. It handles paginated observations, saves raw pages for resumption, and preserves trusted vintage rows on repeat runs. The rebuild writes the ignored `data/derived/mci_point_in_time_v1.json` cache. See [PIT methodology](docs/methodology.md#point-in-time-macro-conditions-index-infrastructure-v1) before interpreting historical results.

Start the backend:

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

In a second terminal, start the frontend:

```powershell
Set-Location C:\Projects\macrolens\frontend
npm ci
npm run dev
```

Open the app and inspect the API:

```powershell
Start-Process 'http://127.0.0.1:5173/#/'
Start-Process 'http://127.0.0.1:5173/#/explore/indicators/UNRATE'
Start-Process 'http://127.0.0.1:5173/#/research/mci'
Start-Process 'http://127.0.0.1:8000/docs'
Invoke-RestMethod 'http://127.0.0.1:8000/health'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/economy/us/brief' | ConvertTo-Json -Depth 20
```

The frontend uses `http://127.0.0.1:8000` by default; set `VITE_API_BASE_URL` to override it. Browser access is allowed for the local Vite origins configured by the API.

## Tests and production build

Backend tests use fixtures/mocks rather than requiring a live FRED download or PostgreSQL server:

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m pytest
Set-Location frontend
npm test -- --maxWorkers=2 --minWorkers=2
npm run build
Set-Location ..
git diff --check
git status --short
git diff --stat
git diff
```

Tests cover data handling, feature/classification rules, PIT reconstruction, API responses, research calculations, routing, UI states and report export. The production bundle is generated in `frontend/dist`; a successful build is not a substitute for browser review. No test-coverage percentage or performance benchmark is claimed.

## Limits and scope

Implemented: the pipeline, six deterministic domain snapshots, numeric Overview/Markdown export, indicator exploration/curated charts, release calendar, current-vintage and PIT MCI, Nasdaq/Bitcoin comparison and lead/lag research, and indicator relationships.

Stored data may lag publishers; revisions change current-vintage readings. Release conventions do not guarantee exact publication times. MCI includes only selected series and requires adequate vintage/reference coverage. Correlation samples vary with missing data and dates; experimental indices are not validated forecasts, recession probabilities or investment signals. Source terms and attribution still apply.

Future ideas are outside the implemented scope: AI integration, consensus/surprises, diagnostics workspace, authentication/accounts, scheduled jobs/notifications, report archive, PDF export and deployment infrastructure. There are no promises or research results associated with these ideas.
