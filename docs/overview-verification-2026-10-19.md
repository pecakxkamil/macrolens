# Overview verification - 2026-10-19

## Scope

Read-only live FRED comparisons covered all 20 underlying Overview series. Each response was archived under `data/raw/overview_review/20261019/` (ignored by Git), including response parameters and observation values. The audit used the latest nonmissing value, not the retrieval date, as the source cutoff. No external provider is called during rendering.

| Series | Latest source period | Before Overview | After Overview | Result |
| --- | --- | --- | --- | --- |
| PAYEMS | 2026-09-01 | 2026-09-01 | 2026-09-01 | Already at source cutoff |
| UNRATE | 2026-09-01 | 2026-09-01 | 2026-09-01 | Already at source cutoff |
| ICSA | 2026-10-10 | 2026-10-03 | 2026-10-10 | Refreshed observations and existing features |
| CPIAUCSL | 2026-09-01 | 2026-08-01 | 2026-09-01 | Refreshed observations and existing features |
| CPILFESL | 2026-09-01 | 2026-08-01 | 2026-09-01 | Refreshed observations and existing features |
| PCEPILFE | 2026-08-01 | 2026-08-01 | 2026-08-01 | Already at source cutoff |
| GDPC1 | 2026-04-01 | 2026-04-01 | 2026-04-01 | Already at source cutoff |
| CFNAI | 2026-08-01 | 2026-08-01 | 2026-08-01 | Already at source cutoff |
| INDPRO | 2026-09-01 | 2026-08-01 | 2026-09-01 | Refreshed observations and existing features |
| PCEC96 | 2026-08-01 | 2026-08-01 | 2026-08-01 | Already at source cutoff |
| DSPIC96 | 2026-08-01 | 2026-08-01 | 2026-08-01 | Already at source cutoff |
| RSAFS | 2026-09-01 | 2026-08-01 | 2026-09-01 | Refreshed observations and existing features |
| HOUST | 2026-08-01 | 2026-08-01 | 2026-08-01 | Already at source cutoff |
| PERMIT | 2026-08-01 | 2026-08-01 | 2026-08-01 | Already at source cutoff |
| MORTGAGE30US | 2026-10-15 | 2026-10-08 | 2026-10-15 | Refreshed observations and existing features |
| DGS2 / DGS10 | 2026-10-15 | 2026-10-07 | 2026-10-15 | Refreshed observations and existing features |
| NFCI | 2026-10-09 | 2026-10-02 | 2026-10-09 | Refreshed observations and existing features |
| DFEDTARL / DFEDTARU | 2026-10-19 | 2026-10-18 | 2026-10-19 | Refreshed both official bounds |

Every after period above matched the stored observations and the selected transformation. The latest raw values also matched the live source values for all 20 series. The Treasury spread uses same-date yields. Monthly source dates are observation-period labels; GDP 2026-04-01 denotes Q2 2026. These dates are not release dates.

For the Fed block, the latest shared **observation date** is 2026-10-19. The lower and upper source histories were **retrieved** on 2026-10-19 at 14:34:33 UTC and 14:34:36 UTC, respectively (16:34 in Europe/Warsaw). The current 3.75-4.00% range has been **effective since** 2026-09-17, as established by the contiguous stored daily bound histories; that effective date is distinct from the observation and retrieval dates. The last change was +25 basis points. These fields do not identify the date of the latest FOMC decision. Official bounds: [DFEDTARL](https://fred.stlouisfed.org/series/DFEDTARL) and [DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU).

## Writes performed

Only these existing ingestion paths ran: `CPIAUCSL`, `CPILFESL`, `DFEDTARL`, `DFEDTARU`, `DGS10`, `DGS2`, `ICSA`, `INDPRO`, `MORTGAGE30US`, `NFCI`, `RSAFS`. Existing configured features were recalculated for the nine non-Fed series; the Fed range reads its two raw observation histories directly. No full ingestion batch, PIT backfill, schema change, provenance change, or methodology change ran.

Trusted ALFRED rows were fingerprinted before and after using count and a hash aggregate of ID, observation date, vintage date, value, real-time end, source and ingestion timestamp. All 1,066,512 trusted rows remained unchanged. The normal FRED conflict guard was retained.

## Presentation

- Percent growth rates, same-month YoY and Fed bounds use two decimal places; unemployment uses one. Grouping separators follow EN/PL locale. Formatting never changes scoring inputs.
- Growth-rate differences are available through the existing keyboard-accessible tooltip. The report keeps the exact difference; the arrow and its color use the displayed precision. Level differences retain explicit units.
- Compact calendar entries show name, date and known Warsaw time. Repeated low-importance H.15 entries have one count summary; each date remains in details and the report. Polish counts use plural rules (for example, 5 publikacji).
- An empty primary calendar list is no longer rendered when only grouped events exist. No empty Markdown list item was reproduced in the downloaded reports.
- FOMC provenance and the existing explanatory text remain in its details block. The main block shows the decision schedule and CME link.

## Limits

This is a point-in-time verification of the provider responses retrieved on 2026-10-19, not a permanent freshness guarantee. Natural publication lags remain: core PCE, real consumption, real disposable income, CFNAI and housing end in August; GDP ends in Q2. Missing periods remain missing. The audit did not refresh other indicators or validate PIT/Research history against new source downloads.


## Verification results

- Backend: `python -m pytest` - 469 passed.
- Frontend: `npm test -- --maxWorkers=2 --minWorkers=2` - 179 passed in the final standalone run. An earlier concurrent run timed out importing the lazy MCI page; the existing test passed on the standalone run without changing Research code or test timeouts.
- Live Chrome: Overview in EN/PL at 1366 px and 390 px; 51 main values and 21 same-month YoY contexts matched the API. Keyboard focus exposed the exact-difference tooltip. No horizontal overflow, clipped comparison tables, console errors, or failed API calls.
- Actual downloaded Markdown: both languages matched the displayed values and periods, retained precise differences and provenance, and had no empty bullets, excess blank-line runs, or duplicate source URLs.
- Production: `npm run build` passed (TypeScript and Vite, 650 modules).
- `git diff --check` passed; only existing line-ending warnings remained.
