# Calendar — ISM Manufacturing and Services, 27 October 2026

## Sources and confirmed horizon

The [official ISM release calendar](https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/)
lists 24 explicit Manufacturing/Services release dates for **2026**: January 5/7
through December 1/3. The monthly reference periods are December 2025 through
November 2026. The January Manufacturing holiday exception (January 5) and July
Services exception (July 6, after the July 3 observed holiday) come from the
published table, not a computed business-day calendar. Planning Forecast rows are
excluded. No 2027 dates are generated from the ordinary first/third-business-day
wording.

Both current ISM releases explicitly describe compiling the report in the month
following the surveyed month. This documents the reference-month rule applied
only to the dates in the published calendar. Each event retains the rule source.
The calendar's generic “EST” clock is corroborated by the releases' explicit
10:00 a.m. **ET** wording. Conversion uses `America/New_York` and
`Europe/Warsaw`; the scheduled clock is independent of PR Newswire's document
publication timestamp and the local retrieval time.

The existing PR Newswire discovery and validated importer were checked at
**2026-10-27T15:35:18.167016+00:00**. They still identified these latest reports:

- [September Manufacturing](https://www.prnewswire.com/news-releases/manufacturing-pmi-at-54-5-september-2026-ism-manufacturing-pmi-report-302894520.html):
  own report month September, document published October 1, headline 54.5, August
  54.6; explicitly announces October data on **November 2 at 10:00 a.m. ET**.
- [September Services](https://www.prnewswire.com/news-releases/services-pmi-at-54-9-september-2026-ism-services-pmi-report-302898421.html):
  own report month September, document published October 5, headline 54.9, August
  55.4; explicitly announces October data on **November 4 at 10:00 a.m. ET**.

Backend access to the annual calendar returned **HTTP 200 with a CAPTCHA form**,
not a usable calendar. It was rejected without solving or bypassing the challenge.
The published 2026 table was reviewed through the official page's web retrieval;
`config/ism_calendar_evidence.json` labels that acquisition method explicitly.
It is saved evidence, not a successful fresh backend network check. The automatic
adapter also extracts the publisher's explicit next-report announcements from
already validated stored documents, without requesting older reports.

## Calendar and result behavior

Both report types enter the existing calendar as `ism_report` events with stable
kind/reference-period identities. The growth category, native table, filters,
sort order, countdown and routes are retained. The shared frontend editorial
configuration gives each exact ISM report three MacroLens stars in Calendar and
Overview. The featured-event selection algorithm and four-event cap are unchanged.
S&P Global PMI is not included in this mapping.

`ism_documents` and `ism_observations` remain the only ISM observation pipeline.
Calendar loading reads them in the same database transaction as other readings;
it makes no provider request and does not query FRED for the local ISM series.
Actual requires a document whose **main report month and series** match the
event, published after its scheduled release instant and available by the current
time. The newest such document version is selected by publication time, retrieval
time and ID. A later report's 12-month table cannot manufacture historical first
prints. Without the matching document Actual remains empty with a specific reason.
Passing the scheduled time or reimporting September cannot create October Actual.

Before publication, Previous prefers a document for the exact preceding report
month; otherwise a matching previous-month observation can be shown with an
explicit current-vintage label. After publication, Previous comes from the same
document as Actual. An earlier document's previous-month value and provenance
remain separate in `previous_before_report`, with `previous_revision_confirmed`
when the two values differ. This is distinct from revising Actual. Neither value
is silently called a historical first print.

All readings are diffusion-index **levels**. Values and differences use index
points, with no percent sign, MoM/YoY transform or new PMI color rule. Forecast
stays empty because consensus is not integrated. Expanded EN/PL details retain
the source URL, document publication time, retrieval time, RAW hash, prior-version
context and the existing personal-use/public-display limitations.

| Report | Release | Warsaw time | Reference period | Actual | Previous |
|---|---|---|---|---:|---:|
| Manufacturing | 2026-11-02 | 16:00 | October 2026 | — | 54.5 pt |
| Services | 2026-11-04 | 16:00 | October 2026 | — | 54.9 pt |
| Manufacturing | 2026-10-01 | 16:00 | September 2026 | 54.5 pt | 54.6 pt |
| Services | 2026-10-05 | 16:00 | September 2026 | 54.9 pt | 55.4 pt |

## Automatic operation and limits

The existing coordinator owns the advisory lock, job budget, cooldown and atomic
brief/chart publication. ISM report discovery/import and the new `ism:calendar`
metadata resource share `OVERVIEW_ISM_INTERVAL_SECONDS` (default six hours,
minimum 900 seconds). There is no extra service or intensive poller. Schedule
failure retains saved dates and explicit announcements; future checks retry at
the same provider cadence. Shorter calendars do not remove absent known periods.
An explicit new announcement can extend the horizon by that event only.

Annual-calendar checking, latest-report discovery, successful result download and
matching-event availability are separate states. A partial calendar result does
not become a successful network check merely because saved dates are usable.
Legacy report checks without the new download-state field retain their old
timestamps rather than receiving invented fresh check metadata.

No additional historical reports are fetched. The stored documents currently
support trustworthy own-report Actual for September 2026 only, for each kind.
Earlier months in their history tables retain their contextual/version limits.
There is no consensus, complete first-release history or public-demo clearance.
The existing ISM use restrictions remain; public availability does not establish
redistribution rights. BLS access/manual-horizon limits and other calendar source
limitations are unchanged. No database reset, ALFRED backfill or MCI/PIT change
is part of this work.

## Verification

- Full backend: **704 passed**; full frontend: **523 passed** across 22 files.
- Synthetic fixtures cover both report types, published exceptions, year rollover,
  IANA DST differences, missing/new/wrong/older documents, duplicate imports,
  earlier previous-month versions, no consensus, absent previous observations,
  CAPTCHA/error retention and the existing ISM interval. No provider calls are
  made by the automatic tests; no test is skipped or given a longer timeout.
- Production build passed with the existing main-chunk warning (**507.49 kB**,
  unchanged 500 kB warning threshold).
- Real API, without response fixtures: future November 2–8 and historical
  September 28–October 5 return the four rows above, with distinct provenance.
- Real browser: EN/PL at **1366 and 390 px**, both report rows, three-star filter,
  units, neutral historical differences, details/Escape and no horizontal page
  overflow. Event text remains 14.5 px; calendar CSS was not changed.

The controlled coordinator job ran **15:55:21–15:55:52 UTC**, honoring all provider
intervals, and published revision `ae3cc2b3-bafc-4566-bec3-0dca21f22e48`. Both ISM
result resources were correctly cached within their existing six-hour interval;
the independent successful live discovery/validation at 15:35 was diagnostic and
did not claim another ingestion. The annual-calendar attempt encountered an HTTP
error, after the earlier diagnostic response had returned a CAPTCHA. Its source
check remains partial and saved dates remain usable.

Live verification identified the existing importer's RAW path contract: paths
are relative to `data/`. The adapter now resolves that location, verifies the
hash and reparses the stored validated document. Regression tests cover this
contract. Derived announcement metadata is invalidated after new document versions
or an adapter upgrade, without issuing an early annual-calendar request. At
**16:01:16 UTC**, a cache-only rebuild under the coordinator's advisory lock
confirmed both explicit November announcements. It preserved original document
retrieval times (October 27, 10:21 UTC), the failed annual-check timestamp and the
coordinator's next-check time. No observations or document history were changed.

Fresh browser/API requests verified both report details and source states in
EN/PL at both widths. Overview shows Manufacturing on November 2 as the fourth
featured event with three stars. Services on November 4 stays outside the current
October 27–November 2 seven-day window. No selection-limit change was needed.
Browser console and API responses showed no application errors. `git diff --check`
passed. Raw diagnostics and screenshots stay ignored under
`data/raw/ism-calendar-2026-10-27/` and existing ISM raw directories.

Manual check: open Calendar → Next week; verify the November 2/4 ISM rows and
their October labels. Use September 28–October 5 for both historical reports;
expand each row and inspect document dates, units and hashes. Enable Only ★★★
and switch EN/PL. Overview follows its existing seven-day scope and four-event
limit, so an out-of-window Services report need not appear in the featured list.

Implementation was validated without a commit or push. A subsequent user
instruction authorized committing and pushing the completed changes.
