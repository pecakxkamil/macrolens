# Calendar finalization — 27 October 2026

## Countdown

The nearest visible publication group keeps one countdown. At least 24 hours is
shown as full 24-hour days; shorter intervals show full hours/minutes, minutes,
or “less than a minute”. EN uses singular/plural day, hour and minute; PL uses
“dzień”/“dni”, “godz.” and “min”. Remaining time is measured from the actual
publication instant, rather than calendar dates or rounded hours.

The former 15-second interval is replaced with a timeout at the next displayed
unit boundary or publication instant. Hidden tabs pause the timer and returning
to a visible tab recomputes from the real clock. No permanent background or left
edge marks the nearest rows; hover, keyboard focus, stars and day headings remain.

## Revised September building permits

The official [BPS current-data page](https://www.census.gov/construction/bps/current.html)
links the [national workbook](https://www.census.gov/construction/bps/permitsbyusreg_cust.xls).
The workbook retrieved at **2026-10-27T13:37:44.397314+00:00** has **1398 thousand
homes/year (SAAR)** for September 2026 and **1403** for August in `Units SA`.
Its SHA-256 is
`fc6ca43eb9d3fefec98fae6fed897ef4e05360ab531d9a68c5d3c514aaf64d96`.
The [BPS schedule](https://www.census.gov/construction/bps/schedule.html) and
[SOC schedule](https://www.census.gov/construction/soc/schedule.html) explicitly
identify October 27 as the revised-permits publication for September. The
updated current file and dated schedule establish the publication evidence;
HTTP Last-Modified alone is not treated as proof of a new publication stage.

The revised-permits clock is **08:00 America/New_York**, or **12:00 UTC / 13:00
Europe/Warsaw** on October 27. It is distinct from the initial NRC report at
08:30 New York. The existing schedule adapter now records that clock only when
the publisher table explicitly supplies it; missing evidence does not fall back
to the initial report's clock. Adapter version 5 invalidates the old schedule
cache at the next permitted coordinator check.

At the first database inspection, FRED still supplied **1400** for September,
from a snapshot dated October 26. Its metadata update marker was October 20.
This is an old pre-revision observation, not the published October 27 result.
The period and PERMIT mapping already existed. Missing stage evidence and an
incorrect shared NRC clock were separate issues from the provider delay.

The reviewed receipt in `config/calendar_period_evidence.json` records the
publisher document, date, period, stage, unit, retrieval time and hash. It does
**not** import the workbook value into observations. Actual remains sourced from
the existing FRED/ALFRED pipeline. A current-vintage result requires a matching
receipt, a newly fetched observation for that period and a provider update on
or after the publication date; a known published value must also match. A
same-day stored vintage cannot override contradictory publisher-value evidence.
An unchanged revised number is accepted when those availability checks succeed;
a change in the number is not itself the publication test.

When Census publication is confirmed but the provider result is not, Actual
remains empty with `revised_permits_provider_pending` in the API and a specific
EN/PL explanation in details. Without stage evidence, the separate reason is
`publication_stage_unconfirmed`. No new Census observation integration or XLS
dependency was added; the workbook reader was used only for this diagnosis.

**Previous remains August 2026: 1403 thousand SAAR.** This preserves the existing
`previous_period` methodology. It is not the earlier September estimate of 1400.
The expanded EN/PL details state both the same-month revision and this comparison
basis explicitly. The GDP same-quarter-estimate policy remains separate.

The normal coordinator job ran **13:59:22–13:59:52 UTC**, respecting the cooldown,
shared lock and request budget. It published revision
`323926f7-95d1-46e1-95d0-06bde56d29bc`. PERMIT metadata was checked successfully
and remained unchanged, with the October 20 update marker. The source job remained
partial because some publisher checks were unavailable; this was not relabelled
as a complete source check. The revised-permits clock was refreshed from the
successfully retrieved SOC schedule.

To distinguish provider delay from application caching, a separate read-only
diagnostic used the existing FRED client and bounded request budget for PERMIT
metadata and observations. At **14:01:03 UTC / 15:01:03 Warsaw**, FRED's actual
observation response still contained **1400** for September and **1403** for
August, with the metadata marker still October 20. No diagnostic observation was
ingested. This confirms **FRED delay**, rather than stale application data/cache,
as the remaining reason for the empty actual. The live API after refresh returned
`2026-10-27T12:00:00Z`, Actual `null`, Previous `1403`, previous period
`2026-08-01`, and `revised_permits_provider_pending`. Fresh EN/PL browser requests
returned HTTP 200 and showed 13:00, the empty actual and the explicit explanation.

## Validation and scope

- Full backend suite: **677 passed**; full frontend suite: **514 passed** across
  22 files. No tests were skipped and no test timeout was increased.
- Production build passed. The existing main-bundle warning remains: **504.37 kB**
  minified, above the 500 kB warning threshold. The threshold was not changed.
- Real API/browser, without response fixtures: EN/PL at **1366, 1024 and 390 px**,
  current and next week. Countdown changed between minutes and full days;
  percentage, index and thousand-unit readings were present. Measured event,
  time and result text is **14.5 px**, column headers **13.5 px**, stars **17 px**.
  Desktop headers and cells share the same widths; no page overflow or permanent
  next-row highlight was present. Permits details retained the publisher link,
  explicit previous-month basis, visible 2 px keyboard focus and Escape closure
  on desktop/mobile. Screenshots were inspected.
- Added two EN/PL regression cases for revised-permits details. They caught and
  resolved duplicate sentence punctuation after the Polish “tys.” abbreviation.
  A full-suite run under concurrent build load also exposed a cold nested-route
  import in the existing Charts navigation test. Loading its real dependencies
  during collection removed compilation from the DOM wait budget; no component
  was mocked, test was skipped, or timeout was increased. The final full suite
  passed.
- `git diff --check` passed before staging.

The current working tree also contains earlier completed Overview explanations,
reading dialogs, source-check/refresh infrastructure, PPI, existing local ISM
document support and Compare Data work. Those dependencies are reviewed together;
this stage adds no ISM calendar integration and changes no MCI/PIT methodology.
Source/raw captures, local database contents, browser captures and runtime files
remain ignored, outside Git. Earlier audit documents retain the results and
limitations as of their own check times.

## Remaining limits

- No consensus provider: forecasts remain unavailable rather than copied from
  previous values or model output.
- BLS requests returned HTTP 403 in the preceding live checks. Automatic adapters
  retain the last good evidence; manually confirmed periods cover only their
  documented bounded horizon. Future BLS periods are not guessed.
- Current-vintage results can contain later revisions. Stored ALFRED intervals
  provide date-level availability, not exact intraday first-release values; the
  stored vintage history is incomplete. No ALFRED backfill was run.
- The permits receipt confirms this publication only. It does not implement
  automatic retrieval of every future revised-permits workbook.

No push, database reset or existing-commit amendment is part of this stage.
