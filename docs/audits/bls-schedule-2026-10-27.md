# BLS automatic schedule audit — 27 October 2026

## Outcome

The existing calendar synchronizer now supports BLS per-publication tables and
monthly lists, conditional HTTP revalidation, an independent daily schedule
interval, and explicit identity-based reconciliation. **Live BLS access remains
blocked in this backend environment. No new automatic BLS records were imported,
and the manually confirmed horizon was not extended.**

Existing uncommitted work was preserved. There were no appearance, forecast,
indicator-calculation or MCI/PIT changes, database resets, history deletion,
ALFRED backfills, commits or pushes.

## Actual access diagnosis

Interpreter: `C:\Projects\macrolens\.venv\Scripts\python.exe`.
Controlled requests started at 2026-10-27 11:14:48 UTC. Both `httpx.Client` with
the existing options and plain `urllib.request.urlopen` with no supplied headers
returned the same result for these official URLs:

| URL | httpx | urllib | Response |
|---|---:|---:|---|
| https://www.bls.gov/schedule/news_release/bls.ics | 403 | 403 | HTML Access Denied, 1,323 bytes |
| https://www.bls.gov/schedule/news_release/empsit.htm | 403 | 403 | Same access-denial document |
| https://www.bls.gov/schedule/2027/01_sched_list.htm | 403 | 403 | Same access-denial document |
| https://www.bls.gov/schedule/ | 403 | 403 | Same access-denial document |

Responses had `Content-Type: text/html`, no content encoding, ETag or
Last-Modified, and no changed final URL. httpx recorded no redirects. No proxy
schemes were configured according to urllib's proxy discovery; no proxy values or
environment secrets were printed. Requests completed within a 20-second timeout.
The body identifies BLS automated-access policy, not a calendar or an ICS file.

This rules out an urllib-only success in this environment, and these responses
were neither decompression errors nor timeouts. The specific access-control rule
responsible for the refusal could not be established. No alternate host, rotating
proxy, browser impersonation or CAPTCHA bypass was attempted.

The adapter retains httpx because the standard-library client did not improve
access. Valid gzip responses are decoded by httpx and covered in offline tests.

## Official sources and formats

The BLS [calendar navigation](https://www.bls.gov/schedule/) links to:

- [Employment Situation](https://www.bls.gov/schedule/news_release/empsit.htm)
- [CPI](https://www.bls.gov/schedule/news_release/cpi.htm)
- [PPI](https://www.bls.gov/schedule/news_release/ppi.htm)
- [Employment Cost Index](https://www.bls.gov/schedule/news_release/eci.htm)
- [JOLTS](https://www.bls.gov/schedule/news_release/jolts.htm)

These tables are preferred over monthly lists and the documented public ICS feed.
They provide explicit reference month/quarter, release date and release time.
The fallback list format is documented by the official
[January 2027 list](https://www.bls.gov/schedule/2027/01_sched_list.htm).
The running pipeline has no search-engine or AI dependency.

The browser research tool could read the official HTML. It showed, for example,
Employment Situation for December 2026 on 8 January 2027 at 08:30 Eastern and ECI
for Q4 2026 on 29 January 2027 at 08:30 Eastern. These were used to review the
formats and year-boundary tests, **not imported or labelled as successful backend
downloads**. The backend could not inspect the current ICS horizon because its
response was 403; the implementation never assumes it covers the HTML horizon.

## Integration and retention rules

- The adapter runs inside `sync_calendar_periods`, through the existing refresh
  coordinator, PostgreSQL advisory lock, cooldown and request budget. No new
  scheduler, background service or indicator-fetching mechanism was introduced.
- `BLS_SCHEDULE_MIN_INTERVAL_SECONDS` defaults to **86400**, independently of the
  unchanged FRED reading interval. Cache state is per official URL; changing the
  requested calendar window does not bypass that URL's minimum interval.
- ETag and Last-Modified are sent conditionally when available. A 304 requires a
  previously validated representation and advances the successful-check date,
  preserving its content-acquisition date. HTTP 200 must have an accepted content
  type and recognizable, complete supported rows; an error/block page is failure.
- A transient network/timeout or 500/502/503/504 gets at most one retry after one
  second. A 403 is not retried. All attempts use the existing request budget.
- Rows upsert by source URL, release group and explicit reference period.
  Unchanged records retain their original evidence retrieval date. A changed
  date/time archives the previous source record in `bls_history`. Missing rows in
  a shorter or narrower response never imply cancellation.
- Active identities use documented precedence: per-release HTML, monthly list,
  explicit-period ICS, older reviewed evidence. Disagreements are recorded in
  `bls_conflicts`, independently of response order. Equal-priority disagreements
  remain unresolved and do not supply a confirmed period/time/result.
- The merged evidence retains the original reviewed file and timestamps. The
  snapshot separately stores attempts, last successful checks, content retrieval,
  source validators and coverage bounds. A shorter ICS cannot erase longer HTML
  evidence. An ICS item without an explicit reference period cannot create one.
- The existing calendar query obtains metadata for already mapped BLS groups even
  when FRED has no dates in the requested window. Confirmed publisher dates can
  then appear through the same API. An explicit moved identity supersedes its
  previous known date without leaving an active duplicate. Unrelated FRED events
  and absent rows remain intact.
- Explicit clocks use IANA America/New_York and convert to Europe/Warsaw. A FRED
  date without publisher evidence does not establish a BLS clock. Schedule evidence
  does not confirm a result; existing future/result guards remain enforced.
- Calendar reads use the updated evidence directly. The shared job publishes a
  new revision for the frontend's existing refresh/refetch flow. BLS schedule
  failures are included in existing calendar check metadata for displayed BLS
  events, independently of FRED successes; no additional UI warning was added.

## Controlled synchronization and retained horizon

The initial request respected an active cooldown and did not start provider work.
After it expired, one controlled job ran for 1–31 January 2027, starting at
**11:22:53 UTC** and completing at **11:23:21 UTC**. It published revision
`c5badeb3-c147-4db5-9a53-014f1e7245e0` with partial status.

All five per-release pages above, January's monthly list, and `bls.ics` returned
HTTP 403. **No BLS source was successfully fetched or imported automatically.**
Consequently there are no new real imported records to present as examples.

| Group | Latest retained confirmed release | Reference period | New automatic extension |
|---|---|---|---|
| Employment Situation: NFP, unemployment, wages | 6 November 2026 | October 2026 | None |
| CPI / core CPI | 10 November 2026 | October 2026 | None |
| PPI | 13 November 2026 | October 2026 | None |
| ECI | 30 October 2026 | Q3 2026 | None |
| JOLTS | No future publisher-period evidence stored | — | None |

Manual supplementation is still needed beyond these horizons while this
environment receives 403. The existing explicit import accepts a lawfully obtained
official per-release HTML document as well as a monthly list or explicit-period
ICS; supply its exact official URL and original retrieval timestamp. For example:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.sync_calendar_periods `
  --import-bls-document "C:\path\empsit.htm" `
  --source-url "https://www.bls.gov/schedule/news_release/empsit.htm" `
  --retrieved-at "2026-10-27T11:00:00+00:00"
```

Replace the example timestamp with the real acquisition time. Importing a saved
document does not manufacture a successful network check. Once valid responses
are available, the same adapter can extend the horizon automatically within the
existing daily schedule checks; this has been verified offline, not demonstrated
against a successful live BLS response here.

## Verification

- Full backend: **658 passed**; frontend: **500 passed** across 21 files.
- Offline tests cover per-release tables, lists, monthly/quarterly periods,
  December/January transitions, DST differences, moved dates, idempotency,
  shortened ICS, conflicts, partial/invalid content, 403, timeout, bounded retries,
  compression, daily limits, conditional 304 and last-good retention. Provider
  calls are mocked; no external site is required by these tests.
- Existing API checked on port 8000 for the current week and January 2027. The
  current-week ECI retains Q3; its publisher check correctly remains partial.
  January has no imported BLS events, consistent with the failed import. No test
  data was injected into the running API.
- Production build passed with the existing main-bundle warning above 500 kB
  (503.57 kB minified). No frontend or CSS source was changed in this task.
- `git diff --check` passed.

Diagnostics and exact response captures:
`data/raw/bls-access-2026-10-27/diagnosis.json` and neighboring files. The controlled
job result is `controlled-refresh.json`; regular synchronization captures and
source outcomes remain in the existing raw/evidence locations.
