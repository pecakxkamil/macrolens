# Calendar periods and readings audit

Checked: 2026-10-26T22:21:38.146000+00:00

Actual stored data and the running API on port 8000 were checked. Existing styles, filters and date controls were preserved. No consensus provider, ALFRED backfill, database reset, MCI/PIT methodology change, commit or push.

## Causes and changes

- Observations already existed for most supported measures. The old binding relied on same-day ALFRED availability, leaving current-vintage-only and future publications unbound.
- Added publisher schedule/report evidence with exact release dates, per-series periods, estimate stages, source URL and retrieval provenance. No monthly lag or latest-observation-pair guess.
- A future actual remains empty. Current-vintage actuals additionally require FRED provider metadata updated on or after the release date, so an old snapshot cannot become a new estimate merely because time passed.
- Previous values use explicit preceding periods; later GDP estimates use the same quarter and an earlier confirmed stored estimate.
- Dated DOL PDFs supply separate initial and continuing reference weeks. Future claims weeks remain unconfirmed without explicit evidence.
- Census identifies October 27 as revised permits, not another housing-starts report. The existing event keeps only its source-confirmed measure.
- FOMC ranges come from official statements, with separate announcement and implementation dates. Daily observations alone never prove a decision. Differences require parallel moves of both target bounds.
- Fixed the coordinator calendar cache to account for a newly requested window while preserving its common lock, cooldown and request budget.
- The live process on 8000 was still running code without include_readings. Its project/venv identity was verified and the local backend restarted; the actual frontend now receives enriched readings.

## Before and after

| Range | Before actual / previous | After actual / previous | Availability check |
|---|---:|---:|---|
| 2026-10-26 to 2026-11-01 | 0 / 0 | 1 / 14 | complete |
| 2026-11-02 to 2026-11-08 | 0 / 0 | 0 / 4 | complete |
| 2026-09-28 to 2026-10-04 | 12 / 12 | 14 / 14 | complete |
| 2026-09-01 to 2026-10-25 | 34 / 34 | 57 / 57 | partial |

Counts include all events, including lower-importance and out-of-scope releases. The September-wide partial state reflects historical FOMC time coverage; the FRED requested-window scope is covered. A complete availability check is not a claim of complete period/result integration.

## Representative past publications

| Publication / measure | Release | Confirmed period | Actual | Previous | Source and version | Remaining limitation |
|---|---|---|---:|---:|---|---|
| Nonfarm payrolls (NFP) | 2026-10-02 | 2026-09-01 | 29 thousand jobs | 133 thousand jobs | [publisher](https://www.bls.gov/schedule/2026/home.htm); stored_date_vintage | date-level, not intraday availability |
| Unemployment rate | 2026-10-02 | 2026-09-01 | 4.2 % | 4.1 % | [publisher](https://www.bls.gov/schedule/2026/home.htm); stored_date_vintage | date-level, not intraday availability |
| Hourly earnings MoM | 2026-10-02 | 2026-09-01 | 0.1324 % | 0.3188 % | [publisher](https://www.bls.gov/schedule/2026/home.htm); current_vintage | may include later revisions; not exact at-release |
| CPI MoM | 2026-10-14 | 2026-09-01 | 0.6485 % | 0.396 % | [publisher](https://www.bls.gov/schedule/2026/home.htm); current_vintage | may include later revisions; not exact at-release |
| Core CPI MoM | 2026-10-14 | 2026-09-01 | 0.3348 % | 0.2898 % | [publisher](https://www.bls.gov/schedule/2026/home.htm); current_vintage | may include later revisions; not exact at-release |
| Producer inflation PPI MoM | 2026-10-15 | 2026-09-01 | 1.3434 % | 0.4703 % | [publisher](https://www.bls.gov/schedule/2026/home.htm); current_vintage | may include later revisions; not exact at-release |
| Headline PCE MoM | 2026-09-30 | 2026-08-01 | 0.3103 % | 0.0503 % | [publisher](https://www.bea.gov/news/schedule/full); current_vintage | may include later revisions; not exact at-release |
| Core PCE MoM | 2026-09-30 | 2026-08-01 | 0.2474 % | 0.1262 % | [publisher](https://www.bea.gov/news/schedule/full); stored_date_vintage | date-level, not intraday availability |
| Real disposable income MoM | 2026-09-30 | 2026-08-01 | -0.0266 % | 0.3105 % | [publisher](https://www.bea.gov/news/schedule/full); stored_date_vintage | date-level, not intraday availability |
| Real consumption MoM | 2026-09-30 | 2026-08-01 | 0.5503 % | 0.0504 % | [publisher](https://www.bea.gov/news/schedule/full); stored_date_vintage | date-level, not intraday availability |
| Real GDP QoQ, annualized | 2026-09-30 | 2026-04-01 | 2.2202 % | 1.4837 % | [publisher](https://www.bea.gov/news/schedule/full); stored_date_vintage | date-level, not intraday availability; previous is earlier Q2 estimate |
| Initial jobless claims | 2026-10-01 | 2026-09-26 | 197000 claims | 198000 claims | [publisher](https://oui.doleta.gov/press/2026/100126.pdf); stored_date_vintage | date-level, not intraday availability |
| Continuing jobless claims | 2026-10-01 | 2026-09-19 | 1699000 claims | 1712000 claims | [publisher](https://oui.doleta.gov/press/2026/100126.pdf); current_vintage | may include later revisions; not exact at-release |
| Housing starts | 2026-10-20 | 2026-09-01 | 1221 thousand homes/year (SAAR) | 1288 thousand homes/year (SAAR) | [publisher](https://www.census.gov/construction/soc/schedule.html); current_vintage | may include later revisions; not exact at-release |
| Building permits | 2026-10-20 | 2026-09-01 | 1400 thousand homes/year (SAAR) | 1403 thousand homes/year (SAAR) | [publisher](https://www.census.gov/construction/soc/schedule.html); current_vintage | may include later revisions; not exact at-release |
| New home sales | 2026-09-24 | 2026-08-01 | 684 thousand homes/year (SAAR) | 643 thousand homes/year (SAAR) | [publisher](https://alfred.stlouisfed.org/series?seid=HSN1F); stored_date_vintage | date-level, not intraday availability |
| Durable goods orders MoM | 2026-10-02 | 2026-08-01 | -0.0714 % | 0.8699 % | [publisher](https://www.census.gov/manufacturing/m3/release_schedule.html); current_vintage | may include later revisions; not exact at-release |
| CFNAI | 2026-10-26 | 2026-09-01 | 0.07 index points | -0.08 index points | [publisher](https://www.chicagofed.org/research/data/data-release-calendar); current_vintage | may include later revisions; not exact at-release |
| NFCI | 2026-10-21 | 2026-10-16 | -0.496 index points | -0.502 index points | [publisher](https://www.chicagofed.org/research/data/data-release-calendar); current_vintage | may include later revisions; not exact at-release |
| Fed target range | 2026-09-16 | 2026-09-16 | 3.75–4.00% | 3.50–3.75% | [publisher](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm); official_release | — |

## Upcoming publications

| Publication / measure | Release | Confirmed period | Actual | Previous | Remaining gap |
|---|---|---|---:|---:|---|
| Durable goods orders MoM | 2026-10-27 | 2026-09-01 | — | -0.0714 % | correctly empty: publication pending |
| New home sales | 2026-10-27 | 2026-09-01 | — | 684 thousand homes/year (SAAR) | correctly empty: publication pending |
| Fed target range | 2026-10-28 | 2026-10-28 | — | 3.75–4.00% | correctly empty: publication pending |
| NFCI | 2026-10-28 | 2026-10-23 | — | -0.496 index points | correctly empty: publication pending |
| Real GDP QoQ, annualized | 2026-10-29 | 2026-07-01 | — | 2.2202 % | correctly empty: publication pending |
| Headline PCE MoM | 2026-10-29 | 2026-09-01 | — | 0.3103 % | correctly empty: publication pending |
| Core PCE MoM | 2026-10-29 | 2026-09-01 | — | 0.2474 % | correctly empty: publication pending |
| Core PCE YoY | 2026-10-29 | 2026-09-01 | — | 3.0076 % | correctly empty: publication pending |
| Real disposable income MoM | 2026-10-29 | 2026-09-01 | — | -0.0266 % | correctly empty: publication pending |
| Real consumption MoM | 2026-10-29 | 2026-09-01 | — | 0.5503 % | correctly empty: publication pending |
| Saving rate | 2026-10-29 | 2026-09-01 | — | 4.1 % | correctly empty: publication pending |
| Initial jobless claims | 2026-10-29 | — | — | — | integration gap: separate claims weeks not confirmed |
| Continuing jobless claims | 2026-10-29 | — | — | — | integration gap: separate claims weeks not confirmed |
| Durable goods orders MoM | 2026-11-03 | 2026-09-01 | — | -0.0714 % | correctly empty: publication pending |
| NFCI | 2026-11-04 | 2026-10-30 | — | — | correctly empty: publication pending; prior value not stored (may itself be awaiting a future release) |
| Initial jobless claims | 2026-11-05 | — | — | — | integration gap: separate claims weeks not confirmed |
| Continuing jobless claims | 2026-11-05 | — | — | — | integration gap: separate claims weeks not confirmed |
| Nonfarm payrolls (NFP) | 2026-11-06 | 2026-10-01 | — | 29 thousand jobs | correctly empty: publication pending |
| Unemployment rate | 2026-11-06 | 2026-10-01 | — | 4.2 % | correctly empty: publication pending |
| Hourly earnings MoM | 2026-11-06 | 2026-10-01 | — | 0.1324 % | correctly empty: publication pending |

## Limits and verification

- Direct BLS requests return HTTP 403. Explicit September-November periods were reviewed on official BLS pages and retained with their retrieval method in config/calendar_period_evidence.json. Other periods are not inferred.
- Census M3 temporarily failed during the coordinated check. The successfully captured official table from the same audit was parsed with its original capture time. Chicago heading whitespace parsing was corrected and its captured official table reprocessed. Failed checks were not relabelled as fresh successful network requests.
- Historical Census dates outside the currently published schedule and unsupported releases can remain unbound. Future claims need explicit publisher evidence for their two separate weeks.
- Current-vintage sources can contain later revisions. Stored ALFRED intervals establish daily, not intraday, availability. Only proven GDP estimate revisions are marked.
- The controlled coordinator run refreshed FRED metadata and release schedules; FRED series outcomes were unchanged. Existing observation history and PIT/MCI artifacts were retained.
- Backend: 193 offline tests passed. Frontend: 496 passed. Production build succeeded with a chunk-size warning above 500 kB. git diff --check passed.
- Actual browser API requests (no response fixtures): EN/PL at 1366 and 390 px, current week, next week and 28 September-4 October. Verified previous values without future actuals, separate claims weeks, GDP estimate difference, details/Escape, tooltip, and no page overflow.
