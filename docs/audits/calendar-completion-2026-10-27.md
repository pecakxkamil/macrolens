# Calendar completion audit — 27 October 2026

The existing calendar evidence adapters, time metadata, refresh coordinator and
reading transformations were extended. Layout, CSS, font sizes, colors, filters
and date controls were preserved. Earlier uncommitted changes were retained.
No database reset, history deletion, ALFRED backfill, MCI/PIT methodology change,
commit or push was performed.

## Times and reference periods

| Publication | Publisher time and zone | Evidence / validity |
|---|---|---|
| CFNAI / NFCI | 08:30 America/New_York | [Chicago Fed calendar](https://www.chicagofed.org/research/data/data-release-calendar), 2026; an explicit per-release clock takes precedence |
| Durable goods advance | 08:30 America/New_York | [Census M3 schedule](https://www.census.gov/manufacturing/m3/release_schedule.html), exact date and stage must match saved schedule evidence |
| Full M3 | 10:00 America/New_York | Same schedule; exact date and stage required |
| Initial / continuing claims | 08:30 America/New_York | [DOL archive and exceptions](https://oui.doleta.gov/unemploy/archive.asp), 2026–2027 |

Times convert through IANA zones. The same 08:30 New York release appears in
Warsaw at 14:30 on 5 March, 13:30 on 12 March, 14:30 on 22 October, 13:30 on
29 October and 14:30 on 5 November 2026. These transitions are covered offline.
Unknown times remain empty with the existing explanation in details.

DOL's weekly reporting definitions in the [ETA 401 handbook](https://www.dol.gov/sites/dolgov/files/ETA/handbooks/2017/ETHand401_5th.pdf),
the archive convention and the [weekly report](https://www.dol.gov/ui/data.pdf)
support separate initial and continuing weeks. The normal Thursday release
concerns initial claims for the preceding Saturday; continuing claims lag that
reference week by one week. The published Wednesday substitutions retain those
weeks: 25 November 2026, 10 November 2027 and 24 November 2027. Their nominal
Thursday dates are cancelled. An unusual weekday requires explicit reference
overrides. Explicit report evidence takes precedence over the rule; the newest
applicable schedule supersedes older overlapping copies, including cancellations.

| Upcoming release | Initial reference week | Continuing reference week | Stored previous values at this check |
|---|---|---|---|
| 29 October 2026 | 24 October | 17 October | 194,000 / 1,728,000 claims |
| 5 November 2026 | 31 October | 24 October | Empty: the preceding reference observations are not yet stored |

No future actual was filled. A future reference week is schedule evidence, not
evidence that its result is available.

## M3 and presentation

27 October is the advance September durable goods release; 3 November is the full
September M3 report. Both events remain, with distinct EN/PL stage names and times.
For both, previous means the preceding month's MoM reading. The full-report
comparison tooltip and details explicitly distinguish this from an advance-to-full
estimate revision. Existing calculations and revision flags were retained.

The policy row reads “Fed decision — interest rates” / “Decyzja Fed — stopy
procentowe”, without an appended date. Its range and announcement/implementation
details remain. Only CFNAI/NFCI calendar readings and differences now consistently
use two decimal places; other measures and calculation precision are unchanged.

## BLS access and manual horizon

Direct requests to the [annual schedule](https://www.bls.gov/schedule/2026/home.htm),
the documented [public calendar feed](https://www.bls.gov/schedule/news_release/bls.ics)
and the public print view returned HTTP 403. No proxy, browser impersonation or
hidden endpoint was used. The existing adapter now tries the documented ICS feed
after annual-page failure and accepts only explicit reference periods. Offline
tests cover successful fallback and unavailable sources; live access still fails.

Saved reviewed evidence and its original 26 October retrieval timestamps remain.
The exact latest confirmed releases are:

| BLS publication | Latest confirmed release | Reference period |
|---|---|---|
| Employment Situation | 6 November 2026 | October 2026 |
| CPI | 10 November 2026 | October 2026 |
| PPI | 13 November 2026 | October 2026 |
| Employment Cost Index | 30 October 2026 | Q3 2026 |

Beyond these dates, obtain an official schedule document through permitted access
and import it into the same evidence snapshot. Supply its original retrieval time,
not the time of import. For example, replace the path and timestamp below:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.sync_calendar_periods `
  --import-bls-document "C:\path\official-bls.ics" `
  --source-url "https://www.bls.gov/schedule/news_release/bls.ics" `
  --retrieved-at "2026-10-27T10:00:00+00:00"
```

The importer also accepts a saved official annual HTML schedule with its matching
source URL. It preserves existing evidence and does not create a successful
network-check record. Source failures remain visible in existing status/details;
successful FRED checks do not count as successful BLS schedule verification.

## Result confirmation and controlled refresh

Repeated-period publications require their own matching publisher report receipt
and newly fetched observations, or a newly stored ALFRED interval for the release
date. An old snapshot, elapsed publication time or changed provider timestamp alone
cannot confirm a new M3 stage, later GDP estimate or revised-permits result.
Receipts retain the exact date, period, series, stage and source. Parsing rejects
headers for an older period or another stage. Current-vintage results can still
contain later revisions; date-level vintages do not establish intraday availability.

Report checks reuse the coordinator's existing job, lock, request budget and
cooldown. A newly elapsed release can invalidate the slow evidence cache; missing
receipts can be retried at the existing cadence when provider metadata indicates
the period is posted. There is no separate timer or polling service. Publication
of the shared revision makes the frontend refetch readings and differences.

A controlled refresh for 26 October–8 November completed with publication revision
`96f49a10-a0b5-44b1-94cd-4b4cd244b554`. DGORDER was unchanged, with provider metadata
still dated 2 October and observations through August. The official advance PDF
still identified the 25 September release for August; it was not attached to
today's September event. BLS was unavailable and Census schedule/full-report
requests timed out, so the overall refresh correctly remained partial.
Historical full M3 or revised-permits results without a matching receipt/new
ALFRED interval remain unconfirmed rather than being accepted from a timestamp.

Today's advance M3 was still before its 12:30 UTC / 13:30 Warsaw publication time
when checked. **No real newly released result was tested.** Offline tests cover
scheduled → awaiting data → confirmed result, rejection of old same-period values,
and frontend refresh of the actual and its difference. There was no forced
cooldown bypass or fabricated live API response.

## Verification

- Full backend suite: **630 passed**, no skipped tests or increased timeouts.
- Full frontend suite: **500 passed** across 21 files; unchanged test timeouts.
- Production build: passed; existing warning for the main bundle above 500 kB
  remains (503.57 kB minified).
- `git diff --check`: passed.
- Real running API on port 8000 and frontend on 5173, with no response fixtures:
  EN/PL at 1366 and 390 px, current and next week; confirmed clocks, separate
  claims weeks and previous values, CFNAI two-decimal actual/difference, Fed name,
  M3 stages, details and Escape, and no horizontal page overflow. Computed event
  text remained 14.5 px and stars 17 px. Desktop/mobile screenshots were reviewed.

Raw source captures are retained in
`data/raw/calendar-completion-2026-10-27/`; the regular refresh also retains its
captures in `data/raw/calendar_periods/` with check outcomes in the existing evidence
snapshot. Failed requests were not relabelled as fresh successful checks.
