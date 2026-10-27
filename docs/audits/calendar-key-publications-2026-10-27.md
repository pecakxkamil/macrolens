# Calendar — existing key publications, 27 October 2026

## Scope and starting state

Extended the existing calendar evidence, time and synchronization modules for
JOLTS, advance retail sales, G.17 industrial production/capacity utilization, and
PPI/ECI clocks. Existing series and transformations were retained. No frontend
component, CSS, filters, colors, column order, Overview implementation, ISM
integration or MCI/PIT methodology was changed. Earlier uncommitted work remains.
No database reset, history deletion, ALFRED backfill, commit or push occurred.

Before this change, future JOLTS, RSAFS and G.17 events had dates and numeric
specifications but no confirmed periods. Their clocks were absent. The nearest
PPI/ECI periods were saved, without clocks. Previous values therefore could not
be supplied for the unbound monthly events. The starting state was checked in
configuration, local evidence and read-only database queries in the preceding
calendar inventory audit.

## Automatically obtained sources

Official navigation was followed from the Census retail home page and the Fed's
G.17 home/About pages. Backend HTTP requests successfully downloaded:

- [Advance retail schedule](https://www.census.gov/retail/release_schedule.html):
  explicit Data Month / Release Date at 8:30 am. The parser selects only the
  Advance Monthly Retail Trade Report table. The older month in the full MRTS
  table, inventory times and e-commerce dates are not substituted for RSAFS.
- [Advance retail report](https://www.census.gov/retail/sales.html): the exact
  announcement date and explicitly named reference month confirm publication.
- [G.17 schedule](https://www.federalreserve.gov/releases/g17/default.htm):
  explicit 2026/2027 dates, 09:15 monthly clock, and noon annual-revision clock.
- [Fed's June 2026 G.17 evaluation](https://www.federalreserve.gov/releases/g17/OMB/2026/OMB_2026.htm):
  documents publication about 15 days after the reference month, including the
  May/mid-June example. This rule is attached to the explicitly scheduled ordinary
  mid-month releases in 2026/2027. It is not applied to delayed/combined releases,
  annual revisions, multiple releases in a month or dates outside the bounded rule.
- [Current G.17 report](https://www.federalreserve.gov/releases/g17/Current/default.htm):
  confirms the publication date and reference month shared by INDPRO and TCU.
  Table header associations identify the year when tables span two years.

There is no unconditional previous-month inference and no latest-observation-pair
fallback. Annual revisions retain their separate clock but are not assigned an
invented single reference month or added as another ordinary monthly result.

These adapters run inside `sync_calendar_periods`, with the existing coordinator,
advisory lock, cooldown and request budget. Missing rows in a narrower response
do not delete saved evidence. Explicit moves of the same period retain history
and supersede the old active calendar date through the existing overlay. Only
publication groups already in this task's scope gain additional future dates.

Future coverage from the downloaded documents:

- RSAFS: 14 future advance releases, 17 November 2026–15 December 2027, covering
  October 2026–November 2027. The explicitly unannounced December 2027 row is ignored.
- G.17: 14 future ordinary monthly releases, 17 November 2026–16 December 2027,
  covering October 2026–November 2027. Both series share the period; each retains
  its own independent observation/transform availability.

## BLS: one-time reviewed evidence, not working automatic access

The existing backend HTTP client still received **403** for the official JOLTS,
PPI and ECI per-publication pages. An ordinary browser navigation to JOLTS also
returned Access Denied. No bypass or paid provider was used. No existing failed
check was relabelled as a successful automatic fetch.

The official pages themselves were readable through the web reading tool. Their
unmodified tool responses were saved, rather than reconstructed as HTML or taken
from search summaries. The existing reviewed-evidence configuration was appended
with explicitly verified rows, retaining all older records and retrieval times:

- JOLTS: 1 September / July; 29 September / August; 3 November / September;
  1 December / October 2026, all at 10:00 America/New_York.
- PPI: 13 November / October and 15 December / November 2026, at 08:30;
  the saved September and October releases also gained reviewed clocks.
- ECI: 30 October / Q3 2026 at 08:30.

Sources were the official [September list](https://www.bls.gov/schedule/2026/09_sched_list.htm),
[October list](https://www.bls.gov/schedule/2026/10_sched_list.htm),
[November list](https://www.bls.gov/schedule/2026/11_sched_list.htm), and the
[JOLTS](https://www.bls.gov/schedule/news_release/jolts.htm),
[PPI](https://www.bls.gov/schedule/news_release/ppi.htm),
[ECI](https://www.bls.gov/schedule/news_release/eci.htm) pages linked by BLS navigation.

The first capture was read at **12:29:15 UTC**; the additional October capture at
**12:46:18 UTC**. Each new row records method, URL, capture path and acquisition
time. This is a one-time reviewed supplement, not an automated backend import of
BLS HTML. The existing BLS parser and daily source cache were reused unchanged
in behavior. Continuing automatic BLS coverage remains blocked; future evidence
after JOLTS 1 December, PPI 15 December and ECI 30 October 2026 still needs a valid
automatic response or another explicitly reviewed/imported official document.

## Readings, clocks and publication guards

All transformations retain their original definitions: JTSJOL level, RSAFS MoM,
INDPRO MoM, TCU percent level, PPIFIS MoM and ECI QoQ. JOLTS renders in millions;
its difference remains correctly expressed in thousands. Percentage-level and
percentage-growth differences use percentage points, not percent changes of rates.

Before publication actual/forecast remain empty. Previous is calculated from the
explicit preceding month/quarter; a later previous value can remain empty because
that preceding period has not yet been published/stored.

For Census/G.17 a result requires a matching report receipt plus newly fetched
stored observations/provider metadata, or a new date-level ALFRED interval.
JOLTS requires a new date-level interval or a newly fetched point for its confirmed
month with corresponding provider metadata. A changed timestamp cannot relabel
an old observation. Current-vintage values are not described as first prints.
Report text is used to confirm availability, not to replace the existing FRED
transform with a rounded number copied from the report.

Clocks are stored in America/New_York and converted through IANA to Europe/Warsaw.
An explicit report clock wins; missing report clocks are filled only from matching
schedule evidence, retaining a separate clock-source URL. In the DST mismatch
week, ECI on 30 October is 13:30 Warsaw. November PPI/retail are 14:30; G.17 is
15:15; JOLTS is 16:00. March/October mismatch cases are covered offline.

## Controlled refresh and real application

An existing normal coordinator job at 12:28 UTC had already stored the new Census
and G.17 schedules. An explicit request during its cooldown did not start another
job. After naturally waiting for the cooldown, the controlled common job ran from
**12:43:34 to 12:44:05 UTC**, publishing revision
`f23671a2-7229-41c4-bf1a-f60b73a97f51`.

Census schedule/report, Fed schedule/method/report checks succeeded. Required
FRED series were checked and unchanged; the existing shared job additionally
detected and ingested a new DGORDER snapshot through its ordinary pipeline.
No new M3 mapping or event type was introduced in this task. Overall status
remained partial because BLS and other independent source checks were incomplete.

Real API responses after that job showed:

| Publication | Release | Period | Actual | Previous |
|---|---|---|---:|---:|
| JOLTS | 29 September 2026 | August | 7.079 million | 7.335 million |
| Retail MoM | 15 October 2026 | September | 0.770841% | 1.288780% |
| Industrial production MoM | 16 October 2026 | September | 0.662558% | 0.063759% |
| Capacity utilization | 16 October 2026 | September | 76.8504% | 76.4184% |
| JOLTS | 3 November 2026 | September | Empty | 7.079 million |
| Retail MoM | 17 November 2026 | October | Empty | 0.770841% |
| Industrial production MoM | 17 November 2026 | October | Empty | 0.662558% |
| Capacity utilization | 17 November 2026 | October | Empty | 76.8504% |
| PPI MoM | 13 November 2026 | October | Empty | 1.343380% |
| ECI QoQ | 30 October 2026 | Q3 | Empty | 0.888292% |

January 2027 API responses also showed the published 15 January Census/G.17 dates
with December 2026 periods, empty actuals and unavailable future previous values.
The unrelated 28 September annual retail revision remains unbound; it was not
misrepresented as another ordinary advance report. Older exceptional G.17 releases
remain outside the bounded monthly rule.

## Validation

- Full backend: **675 passed**. Full frontend: **502 passed** across 21 files.
- Fixtures cover explicit periods, year changes, G.17 shared periods/independent
  series availability, exceptional clocks, DST, moved dates without duplicates,
  missing/partial responses, 403 and retention, future empty readings, and result
  transitions. No provider calls are needed by automated tests.
- Production build passed; existing main-bundle warning remains at 503.65 kB.
  A TypeScript type widening in the new test was corrected before the successful
  build; no compiler or test timeout was relaxed.
  The new G.17 provenance label was added to the existing Polish translations.
- Real API/frontend, no response fixtures: EN/PL at 1366 and 390 px, historical
  and future windows; actual/previous values, percent/million units, differences,
  clocks, details/Escape and no horizontal overflow. Screenshots were reviewed.
  Event text remains 14.5 px, with existing layout/styles.
- `git diff --check` passed.

Captures, exact outcomes, the job result and browser assertions are retained under
`data/raw/calendar-key-2026-10-27/`; standard job captures remain in the existing
`data/raw/calendar_periods/` location. No live future JOLTS, retail or G.17 result
was claimed to have been released during this verification.
