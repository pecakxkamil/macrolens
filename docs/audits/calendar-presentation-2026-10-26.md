# Compact calendar presentation - 2026-10-26

Presentation only. The existing API, event/result bindings, times, editorial stars, filters, ranges, background-refresh coordinator and economic methodology remain unchanged.

## Final behavior

- One ordinary six-cell row per measure, or one row for a nonnumeric event.
- One shared desktop column header; full-date day headings.
- Publication affiliation, full units, transformations, missing-value reasons, current-vintage/date-vintage provenance and confirmed revisions remain in the selected measure's details.
- Confirmed periods use a short month/quarter/date; unknown periods add no suffix.
- Names follow the existing transform, including MoM, YoY and absolute NFP change. GDP annualization remains explicit in details.
- Compact units accompany values, with full units retained in details. Empty cells and unknown times show a dash.
- Timezone appears above the table; times omit the repeated PL suffix. Unknown times retain the existing sort-after-confirmed-times behavior.
- The nearest simultaneous group shares its highlight and has one compact countdown.
- Name buttons support Enter and expose expanded state/controls; row clicks also open details. Escape closes details and returns focus to the name. Links remain reachable with Tab.

## Verified saved data

Current week 2026-10-26 through 2026-11-01: 16 publication groups, 37 numeric measures and one nonnumeric FOMC event. All 37 measures have unconfirmed reference periods and null actual/previous values. Default two/three-star filtering displays 18 ordinary rows; clearing filters displays 38.

These gaps were not repaired by hiding metadata. A scheduled release date does not establish which observation period belongs to that event. The existing binding logic requires stored evidence, then the exact previous period for the same transformation. Available current observations in Explore Data are not substituted for that missing evidence, and no reference periods or times were inferred.

Historical range 2026-09-28 through 2026-10-04: 37 measures, 12 confirmed actual/previous pairs and 25 unconfirmed reference periods. GDP still shows 2.22% versus 1.48% for Q2 2026, with the previous estimate of the same quarter and confirmed revision retained in details.

The running user API on port 8000 exposes only start_date/end_date/category parameters; it is an older process that does not return include_readings enrichment. Restarting that backend is required to load the already-existing enriched calendar implementation. Verification read the current code through an owned helper on 8001. Browser checks replayed the actual saved GET responses and intercepted refresh requests, so no provider ingestion or database update was initiated by this task. Helper processes were closed after review.

## Checks

- Full frontend suite: 456 passed across 20 files.
- Production build: passed, 663 modules, no chunk-size warning.
- git diff --check: passed; Git reports an existing line-ending normalization warning in tests/test_release_calendar.py.
- Actual saved data in Chrome: EN/PL at 1366 and 390 px, one header, six cells per row, all three numerical fields retained, no main-row technical metadata, no horizontal page overflow.
- Enter/Tab/Escape, row/name expansion, local filters, confirmed revision details and exact GDP values verified.
- No backend changes or backend test rerun in this presentation task. No commit or push.
