# MacroLens

MacroLens collects and validates US macroeconomic data, turns observations into readable indicators, and explains them through a dashboard, a downloadable report and documented historical research.

This portfolio project demonstrates a reproducible data pipeline, SQL storage, time-series transformations, data-quality checks and communication of analytical limitations. It uses deterministic rules; it does not provide economic forecasts or trading recommendations.

## Recent updates — 27 October 2026

Since the previous GitHub update:

- **Overview:** readable current/previous comparisons, PPI and local ISM readings, deterministic EN/PL explanations, indicator-history dialogs and a Markdown report with source and version details.
- **Calendar:** larger, aligned readings; responsive EN/PL layout; reference periods, actual/previous values and neutral comparisons; official FOMC decisions; and a readable countdown without permanent row highlighting. Revised building permits retain their separate publication clock and explicit provider-delay status.
- **ISM Manufacturing and Services:** confirmed 2026 release dates, reference months, IANA timezone conversion and shared editorial three-star importance. Calendar results reuse the existing validated document pipeline and retain document versions, provenance and previous-month revisions. The Overview preview still selects at most four events.
- **Refresh and navigation:** shared source checks, provider budgets, cache invalidation and last-good-data retention; Explore Data/Research navigation and expanded Indicator Relationships comparisons with the existing market histories.

Latest validation: **704 backend tests and 523 frontend tests passed**, production build passed, and real EN/PL browser checks passed at 1366 and 390 px. The build retains a main-bundle size warning. See the [calendar finalization audit](docs/audits/calendar-finalization-2026-10-27.md) and [ISM calendar audit](docs/audits/calendar-ism-2026-10-27.md) for evidence and scope.

Limits remain explicit: no consensus forecasts, BLS HTTP 403 with only a bounded manually confirmed period horizon, current-vintage revisions and incomplete release-version history. Automatic access to the annual ISM calendar can fail on CAPTCHA/HTTP errors; saved confirmed dates and explicit report announcements remain usable. Existing ISM personal-use/public-display restrictions still apply. Local databases, raw source captures, credentials and runtime artifacts are not included in Git.

## Product walkthrough

The application has four main sections, designed for a short demonstration:

| Section | What to inspect | Route |
| --- | --- | --- |
| **Overview** | Six compact domains with latest and previous readings, observation periods, indicator-history links, upcoming releases and a full Markdown report | `#/` |
| **Calendar** | USA publication groups, calendar-week/custom dates, shared importance filters, confirmed reference-period results and source/version details | `#/calendar` |
| **Explore Data** | Select a domain and indicator, inspect its history and available transformations, change the date range, and check units, definitions and sources. Switch to existing curated chart sets when useful. | `#/explore/indicators`, `#/explore/charts` |
| **Research** | Switch between Macro Conditions Index, Macro-Market Analysis, and Indicator Relationships. Inspect their separate methods, samples, missing data and limitations. | `#/research/mci`, `#/research/macro-market`, `#/research/relationships` |

Overview prioritizes 21 current-vintage comparison rows and an official Fed target-range block across six domains. The Labor card shows NFP monthly change, unemployment, raw weekly initial claims with an exact-week 4W-average context, JOLTS levels in millions, and hourly earnings MoM with same-month YoY context. Tables show current and previous values and observation periods; complete three-period comparisons, sources and metadata remain in the Markdown report. Indicator names open their existing Explore Data history, measures and source definitions. Arrows retain numeric direction; JOLTS and wage changes use neutral colors. Domain cards keep natural heights rather than stretching to Labor's five rows. Existing backend Macro State classifications remain available through the API and in the report's audit appendix.

**View full calendar** opens the main Calendar tab at `#/calendar`; the old `#/overview/calendar` address remains compatible. Overview retains a seven-day preview of selected events; routine releases remain in the full calendar and report. Known release times use official publisher conventions and timezone-aware Europe/Warsaw conversion; unknown times remain explicit.

MCI is an **experimental descriptive index**, available in Research. Its 50-point reference is not a validated recession or economic-health threshold. Macro-Market Analysis combines the existing market comparison and lead/lag analysis; its correlations depend on the selected asset, dates and method. Indicator Relationships now compares 2-3 configured macro measures and/or the existing Nasdaq Composite and Bitcoin histories, retaining its separate synchronization rules.

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

Overview shows the next stored FOMC decision independently of the seven-day macro preview. The main calendar also includes these decisions under Financial Conditions, with high importance, a separate `event_id` and **no FRED release ID or mapped indicator**.

Refresh explicitly from the repository root (no API key or database migration):

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m app.ingestion.sync_fomc_calendar
```

The command reads the [Federal Reserve meeting calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), keeps current-year and published future-year meetings, and selects the final meeting day. It verifies future decision times against the [official monthly calendars](https://www.federalreserve.gov/newsevents/2026-october.htm), matching **FOMC Meeting**, rather than minutes or press conferences. Only an explicit matching time is stored; otherwise time is null. Eastern times use `America/New_York`, with standard timezone conversion to UTC and Europe/Warsaw. The [Fed's research documentation](https://www.federalreserve.gov/econres/feds/files/2021074pap.pdf) describes the Eastern-time convention. Dates/times may change, and future-year meetings are tentative until confirmed by the Fed.

Immutable source HTML and URL/retrieval/status metadata are retained in ignored `data/raw/federal_reserve/fomc/`. The normalized schedule is atomically replaced at ignored `data/derived/fomc_calendar_v1.json`; repeated refreshes do not duplicate events. Failed schedule downloads/parsing preserve the last successful snapshot. A missing monthly page leaves its time unknown. Calendar GET requests only read this file. Overview can request the shared background check described below; a new checkout needs the additive refresh schema. Missing, unreadable or exhausted schedules produce an unavailable next-decision message without blocking the macro brief. Retrieval dates remain visible; there is no invented age threshold or guarantee that the saved schedule is current. Re-run the command to check updates. Existing FRED release sync remains separate.

**CME FedWatch: link-only variant.** No authorized CME API subscription/credentials or display/export entitlement is configured. The UI/report link to [CME FedWatch](https://www.cmegroup.com/fedwatch), explicitly state that probabilities are not integrated, and contain no probability snapshots, histories or official target-range estimate. The effective federal funds reading remains a distinct observed rate. A future data integration would require authorized [official FedWatch API](https://www.cmegroup.com/market-data/market-data-api/fedwatch-api.html) access, EOD data and history for the same meeting, and confirmation of rights for display, local retention and Markdown export. No account, subscription, scraping substitute or probability engine was added. See [CME's methodology](https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html).

**PMI: local imports only.** ISM Manufacturing and Services PMI use explicitly supplied ISM releases on PR Newswire. See Local ISM PMI release imports below. No FRED replacement, third-party history or public redistribution rights are assumed. S&P PMI and CME probabilities remain unconfigured.

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

## Indicator Relationships comparison lab

Open `#/research/relationships`. Choose two macro/asset sources and optionally a third, then select an available stored macro transformation. The catalog comes from active configured macro metadata and stored v1 feature names, plus only `NASDAQCOM` (Nasdaq Composite, not Nasdaq-100) and `CBBTCUSD` (Bitcoin). Assets offer stored prices only. Quick presets use this same catalog. Source history is loaded locally; no provider refresh occurs on page load.

- The existing Relationships alignment is unchanged: lowest selected frequency; latest finite observation **inside** each ISO day/week, calendar month or quarter. No earlier-period carry and no interpolation. Tooltips show actual source observation dates.
- This is current-vintage comparison by observation period, not publication-date availability, PIT reconstruction or a backtest. A quarterly GDP observation can therefore align with prices in its observation quarter even though it was published later.
- Actual values retain compatible-unit axes. Ratio indexing is enabled only for raw/level measures with strictly positive selected values and a shared period. Percent rate levels, all non-level transformations, CFNAI and NFCI are excluded. No alternative normalization was introduced.
- Pearson correlation uses the selected **unindexed** measures, with pairwise counts and first/last paired periods. Fewer than three pairs or zero variance gives unavailable correlation. Price-level correlations can reflect trends; they are not return correlations or predictive evidence.
- Stored non-level macro features undergo a Relationships-only calendar check against the same raw snapshot loader and `feature_as_of_date` used by the existing feature pipeline. Each source window must contain every required consecutive monthly, quarterly or weekly observation, including observations before the display range. Missing computation provenance, unsupported cadence, gaps, or extra noncanonical dates exclude that feature point. The UI reports excluded counts. No formulas, database values, MCI/PIT or other history endpoints are changed.

The gap restriction covers `mom`, `qoq`, `qoq_annualized`, `annualized_3m`, `yoy`, `monthly_change`, payroll-change averages, `change_3m/6m/4w/13w` and moving averages. Weekly YoY requires all 53 source weeks; monthly YoY requires 13 months and quarterly YoY five quarters. This verifies calendar dependencies, not economic accuracy or source freshness. Feature catalog entries mean stored transformations exist; a selected range may still have excluded points or no usable observations.

The additive `/api/v1/relationships/sources` endpoint exposes the configured catalog. `/api/v1/relationships/compare` validates source and transformation selections on the server, rejects duplicate raw/level aliases, returns `indexing` eligibility, excluded-point counts and paired-period ranges. Assets reuse the existing latest-vintage raw SQL, not the month-end/price-age alignment engines from Market Comparison or Lead/Lag. Market attribution and source limitations still apply.

Manual check: select UNRATE + INDPRO MoM + Bitcoin; inspect monthly alignment, separate units and three correlations. Select UNRATE + Nasdaq Composite + Bitcoin. Select GDP QoQ annualized + Bitcoin and inspect quarterly source dates. Indexing should be disabled for these rate selections. Select INDPRO observed level + Nasdaq Composite + Bitcoin to enable index-100 display; correlations and pair counts must remain unchanged when toggling display modes. Remove the third series, switch ranges and EN/PL, and inspect missing/error states. No ingestion or backfill is required for already stored histories.

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


### Headline producer prices (PPIFIS)

PPI Final Demand is available in the inflation catalog, Explore Data, Compare Data,
and as the fourth Inflation row in Overview and its Markdown report. Raw values
are a seasonally adjusted index (Nov 2009=100), not percent changes. Only MoM is
configured. Its previous input must be the preceding calendar month; missing
months produce no feature value. No PPI YoY, classification or MCI component is
added. The existing release-calendar sync links the series to its FRED release.

Refresh only this series with the established pipeline:

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m app.database.sync_series PPIFIS
.\.venv\Scripts\python.exe -m app.ingestion.ingest_series PPIFIS
.\.venv\Scripts\python.exe -m app.analytics.compute_features PPIFIS
```


## Local ISM PMI release imports

ISM_MANUFACTURING_PMI and ISM_SERVICES_PMI are monthly diffusion index levels (index points), sourced from ISM releases on PR Newswire, not FRED/ALFRED. They are raw-only: no percent MoM/YoY and no ratio indexing. They do not enter Macro State classifications or MCI/PIT. CFNAI remains available in research and its existing computations.

Apply the additive, idempotent tables with `.\.venv\Scripts\python.exe -m app.database.init_db`.
From the repository root:

```powershell
$manufacturingUrl = 'https://www.prnewswire.com/news-releases/manufacturing-pmi-at-54-5-september-2026-ism-manufacturing-pmi-report-302894520.html'
$servicesUrl = 'https://www.prnewswire.com/news-releases/services-pmi-at-54-9-september-2026-ism-services-pmi-report-302898421.html'
.\.venv\Scripts\python.exe -m app.ingestion.import_ism manufacturing $manufacturingUrl --dry-run
.\.venv\Scripts\python.exe -m app.ingestion.import_ism services $servicesUrl --dry-run
.\.venv\Scripts\python.exe -m app.ingestion.import_ism manufacturing $manufacturingUrl
.\.venv\Scripts\python.exe -m app.ingestion.import_ism services $servicesUrl
```

The explicit importer accepts a supplied release URL. Overview also discovers the latest Manufacturing and Services reports from the public ISM publisher listing on PR Newswire. Discovery validates report kind/month and rejects ambiguous or older documents; it reuses this importer. There is no scheduler or access-block bypass. The importer validates the ISM publisher, report kind/month, named history table, headline/body/table agreement, 12 consecutive unique months and finite values in [0,100]. Changed or incomplete structures fail before database writes; dry-run never writes the database or RAW.

Immutable HTML bytes are saved under ignored `data/raw/ism/`; documents retain SHA-256, source URL, publication timestamp and retrieval timestamp. Identical responses do not duplicate document/observation rows. Revisions retain each document; current-vintage chooses the latest publication timestamp, with retrieval timestamp and document ID as tie-breakers. Older documents cannot override a later publication. Historical observation months are not assigned a fabricated first-release date: document dates belong to the document. This is not full PIT history. Initial coverage comes from the 12-month tables; longer selected chart ranges are never filled or stretched. Later explicit imports may extend coverage.

Local personal use only. Technical access does not establish permission for public display, public demo, redistribution or external export; verify ISM/PR Newswire terms before any such use. No open license is presumed. Do not publish RAW, imported datasets, respondent comments or report text. The UI/report carries source attribution and document provenance, not commentary excerpts. No Bellwether or DBnomics history is imported.


### New-data availability checks

Overview distinguishes observation periods, publication dates, retrieval times and explicit checks for new data. Successful/no-change FRED refreshes, FRED calendar syncs and Federal Reserve schedule refreshes record UTC attempts/results in `source_check_runs`. Failures retain previous successful checks; check scope, errors and interrupted attempts remain available in the brief API metadata. Brief/report GET requests and feature computation do not contact providers. After displaying the saved brief, Overview sends a separate POST asking the backend to start or share a background availability check.

Apply both additive metadata/cache migrations once; they do not reset observation, feature or ISM tables:

```powershell
Set-Location C:\Projects\macrolens
Get-Content .\app\database\source_checks.sql -Raw | docker compose exec -T postgres psql -U macrolens -d macrolens -v ON_ERROR_STOP=1
Get-Content .\app\database\overview_refresh.sql -Raw | docker compose exec -T postgres psql -U macrolens -d macrolens -v ON_ERROR_STOP=1
```

Existing explicit processes (run only the refreshes you intend):

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.ingest_series UNRATE
.\.venv\Scripts\python.exe -m app.analytics.compute_features UNRATE
.\.venv\Scripts\python.exe -m app.ingestion.sync_release_calendar --start-date 2026-10-23 --end-date 2027-04-23
.\.venv\Scripts\python.exe -m app.ingestion.sync_fomc_calendar
```

Replace the series/date window deliberately. The first command checks that configured series through FRED; feature computation only updates local derived data and never advances the availability-check timestamp. The FRED calendar record includes its requested window and active configured series. Fed target bounds use the same FRED series process (`DFEDTARL`, `DFEDTARU`), independently of the direct Fed schedule refresh. Batch ingestion already calls the same per-series process, without a second synchronization system.

Coverage includes the 21 headline readings, existing domain snapshot/detail inputs, both Fed target bounds, the FRED release calendar and the direct Fed schedule. The displayed watermark is the **oldest latest successful check among covered inputs**, never one series' newest check applied to the whole dashboard. Missing/error/partial sources are recorded in API metadata, with no arbitrary age threshold. Calendar coverage must include today's seven-day Overview window and the required FRED series. An old window does not establish current calendar coverage. With no trustworthy check timestamp the header line is omitted. Before new provenance is recorded, the existing explicit Fed snapshot retrieval confirms only its stored meeting-date fetch; it does not confirm checks of other sources or complete decision-time verification.

Overview checks all required FRED series (including both target bounds), the release calendar, the direct Fed schedule and both ISM reports. PR Newswire discovery must confirm the latest report kind, observation month and document date. A manually supplied URL, reimport or failed discovery does not confirm the latest publication. If discovery fails, manual import remains available and coverage stays partial. Unknown decision times in the displayed calendar window or the separately displayed next FOMC decision keep Overview partial. Missing times for more distant meetings affect future-schedule completeness only; times are never guessed. Public display/export rights still require verification.

### Automatic Overview refresh

On entry and return to a visible tab, Overview displays its stored publication first and requests `POST /api/v1/economy/us/brief/refresh`. The backend controls cadence with a shared PostgreSQL advisory lock, including across Uvicorn workers. Concurrent callers share the running job. `GET` on the same endpoint only polls status. Once finished, the client replaces the aggregate as one publication; chart histories use the same revision ID. Report download reads that saved aggregate and records a running check when applicable. No separate queue or scheduler is required.

The defaults are a 900-second minimum for FRED checks, 21,600 seconds for calendars/ISM, and at least a 900-second retry delay. Configure `OVERVIEW_REFRESH_INTERVAL_SECONDS`, `OVERVIEW_REFRESH_RETRY_SECONDS`, `OVERVIEW_CALENDAR_INTERVAL_SECONDS` and `OVERVIEW_ISM_INTERVAL_SECONDS`. FRED requests are spaced by 0.6 seconds during this job; HTTP 429 stops additional FRED calls. `OVERVIEW_REFRESH_TIMEOUT_SECONDS` defaults to 600 seconds between requests, in addition to individual HTTP and database timeouts. Polling is bounded to 15 minutes, pauses while hidden and does not start new jobs. These settings do not guarantee immediate publication availability.

FRED metadata is checked first. When its update marker, local inventory or transform configuration changes, the existing pipeline reloads the current snapshot over the already stored observation range, including older revisions, then recomputes the existing features. This is not an ALFRED/vintage backfill and does not extend history backward. Successful sources publish raw/derived changes and the saved Overview together in one database transaction; failed sources roll back to savepoints. The last publication survives a fatal job failure. Latest attempt and last success are separate, timezone-aware records; no-change checks count as success. The displayed coverage time is the conservative watermark, not the assembly time or a publication date. Source-check logs remain independent of the data transaction, recording provider attempts even if publication fails.

`overview_publications` retains eight disposable brief/chart cache generations; expired chart revisions return HTTP 409 and require reloading Overview. Source observations, feature history and PIT caches are not removed. The direct Fed normalized file uses its existing atomic file replacement; it is not part of the PostgreSQL transaction. Application shutdown interrupts the in-process worker; the next request detects a released lock, retains the prior publication and applies retry backoff. Restart the backend after changing configuration or code.

To invoke the same controlled process explicitly (it honors cadence and may return the existing result):

```powershell
Set-Location C:\Projects\macrolens
.\.venv\Scripts\python.exe -m app.analytics.overview_refresh --wait
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/economy/us/brief/refresh'
```

This does not download ALFRED vintages, rebuild PIT MCI, fetch consensus or integrate FedWatch probabilities. The browser needs the local API/database and configured FRED credentials. Without the additive schema, stored data remains readable with an explicit unavailable-check status; no historical timestamps are fabricated.

The generated EN/PL explanation audit for the verified saved publication is [overview-explanations-2026-10-26.md](docs/audits/overview-explanations-2026-10-26.md). It records actual outputs from `brief/explanationAudit.ts`, which reuses the same interpretation and explanation functions as Overview; no audit export button is added.

Overview availability status is scoped to its saved indicator inputs, displayed calendar window and separately displayed next FOMC decision. A read-only API projection exposes `status_scope`, `full_scope_status`, per-source `overview_status` and `fomc_schedule` completeness metadata. The saved refresh job/source results remain unchanged. Later missing decision times and monthly-page download errors remain in Check details and report audit metadata. A successful download without a confirmed time is distinguished from a failed request; legacy checks without that evidence remain unclassified rather than receiving invented success metadata. This projection neither fetches providers nor rewrites saved publications or source data.

### Main economic calendar

Open `#/calendar` from the main navigation. Both `#/overview/calendar` and the original `#/calendar` entry resolve to this view. Overview retains its compact upcoming list and links to the same calendar. Editorial stars reuse the Overview rules; source high/medium/low classifications are unchanged. Default filters show known two/three-star releases; Clear filters includes low and unknown importance. Day/week calculations use Europe/Warsaw, with Monday-Sunday weeks, explicit date ranges and a 366-day inclusive maximum. Filters only operate on the loaded response.

The existing `GET /api/v1/calendar` accepts `include_readings=true`. It reads stored release groups, official Fed schedule data, mapped indicators and results in one repeatable-read database transaction; it never contacts providers. The original endpoint without this flag remains compatible. Scheduled times are converted through IANA timezones. The closest visible future timed publications share the same countdown when simultaneous; elapsed time alone never creates a numerical result.

Calendar result bindings are deliberately conservative. `app/analytics/calendar_readings.py` maps exact FRED release IDs and series IDs to the existing measure formulas. Stored ALFRED real-time intervals can tie a newly introduced observation period to a stored release day. Explicitly shared monthly reports (Employment, CPI, Income/Outlays and Residential Construction) can establish a common month for related measures. Claims reference weeks are resolved separately. A GDP revision can instead compare the earlier estimate of the same quarter. Missing periods, interval expiration and unknown mappings remain missing. No new ALFRED download or MCI/PIT change is required.

When a stored date-level vintage is available, it is used and labelled accordingly; this is not proof of the exact intraday actual-at-release value. A confirmed report month with only a current stored value is labelled current-vintage and may include later revisions. Revision badges require actual evidence of a changed stored estimate, not an assumption. Future reference periods are not inferred from publication month or the latest observation. As a result, actual/previous fields can legitimately remain blank even when Explore Data has recent context. There is no consensus integration, and forecast fields are always unavailable with an accessible explanation. Source attribution and measure/vintage details are available by expansion.

The calendar reuses the same backend refresh coordinator, PostgreSQL advisory lock, request budget and provider intervals as Overview. It passes the selected range to the existing refresh POST. A selected range is registered while holding the shared lock and is used at the next permitted calendar sync; it does not bypass the calendar minimum interval. After a running job completes, a range not covered by it is registered for the next permitted check. The latest registered range wins; this is not a new queue. A distant range that does not overlap the normal horizon is checked by itself to avoid fetching all intervening years. All active configured FRED calendar series are included in that job. The API reports selected-range coverage separately from whole-job outcomes and distant missing Fed times; unverified ranges never receive a fabricated successful check date. No provider is called by filter clicks.

Manual verification: open Calendar, switch the day/week presets, use a custom range such as 2026-09-28 through 2026-10-04 if retained in your local database, expand GDP and verify whether Previous is the earlier estimate of the same quarter, and inspect the vintage labels on Income/Outlays and Employment measures. Test EN/PL, Only three stars, Clear filters, keyboard Enter/Escape and the old calendar address. Coverage depends on your actual saved vintages and source-check metadata; a new checkout may show no mapped results.

The nearest visible publication group has one EN/PL countdown: full 24-hour days from 24 hours onward, then full hours/minutes, minutes, or less than a minute. Its timer wakes at the next displayed-unit boundary and pauses while hidden. Event rows have the same resting appearance; hover and keyboard focus remain visible.

Both ISM PMI reports now appear in Calendar with the existing local document source, growth category and shared MacroLens editorial three-star importance. The published 2026 ISM table supplies exact dates, including holiday exceptions; validated reports document the following-month reference period, ET clock and explicit next-release announcements. The annual calendar can be blocked by a CAPTCHA: this remains a failed automatic check, while reviewed confirmed dates and explicit report announcements remain usable. Actual requires the document's own report month; Previous after publication uses that document's prior-month value, with any earlier version shown separately. There is no consensus or complete first-release history. See the [ISM calendar audit](docs/audits/calendar-ism-2026-10-27.md) for sources, bounded coverage and verification. Existing ISM personal-use/public-display restrictions remain; this is not public-demo clearance.

Revised building permits use the separate clock explicitly documented in the Census schedule (08:00 New York, versus 08:30 for initial NRC). Previous continues to mean the preceding month, not the earlier estimate of the revised month. A confirmed publisher receipt is distinct from availability in FRED; if the provider still supplies the old estimate, Actual stays blank with its specific reason in details. See the [calendar finalization audit](docs/audits/calendar-finalization-2026-10-27.md) for the October 27 evidence and validation. This stage adds no automatic Census workbook observation integration.
