# CPI/Core CPI V4 release and integrity

This release adds CPI ingestion and calendar presentation while retaining the
existing Employment integration and Forecast F1 methodology. It also extends
the independent CI byte-integrity check to the explicitly approved V4 inventory.

## Data contract

The four BLS contracts are CUSR0000SA0 / CUSR0000SA0L1E for headline/core
month-over-month SA, and CUUR0000SA0 / CUUR0000SA0L1E for year-over-year NSA.
Existing FRED SA history remains separate. An anonymous BLS batch supplies index
levels. Rates derived with Decimal and rounded to one decimal are identified
as derived rates; they are not represented as API fields containing published
percent changes. Original levels, footnotes, capture hashes and calculation
inputs remain available in provenance.

The October 2026 capture produces headline 0.4 / 0.6 and core 0.3 / 0.3.
Core's displayed comparison is neutral. Missing annual base data is terminal
only with publisher evidence: no interpolation, zero substitution, SA/NSA
mixing or endless release polling. Annual NSA readings do not consume SA
forecast evidence. Trends and explanations use the selected measure contract.

The CPI worker uses the existing backend lifecycle and a confirmed 48-hour
release catch-up window. Employment retains its two-hour window. Both use
one durable BLS lease and budget: eight claims per rolling day and at least
900 seconds between attempts, with persisted refusals/backoff and Retry-After.
A complete batch, including terminal unavailable annual readings, stops
additional attempts. Operation requires a running backend and confirmed
schedule evidence; this is not a guaranteed publication SLA.

## Authorization and CI

The independently reviewed authorization plan has canonical SHA-256:

`ebfe454621a598db1745690e1d94b0d35227add8916f2823a35f9595280e689c`

Its artifact map has canonical SHA-256:

`90af2f8758569aa1ac0667855827b0b67167313ea21ec0f4cc05073cf0c23cbb`

The new public baseline is a static extract of that map: **161 exact files and
three library versions, 164 artifacts total**. It contains no database identity,
runtime token, original provider documents or target-specific activation plan.
The checker validates the pinned plan/map digests before reading checkout files;
it does not regenerate expected hashes from the checkout under test.

The historical V3 baseline and approval anchors remain intact. V4 is the CI
default and is explicitly selected by the workflow. Historical V3 verification
requires `--authorization-version 3`; it cannot approve the V4 checkout.

Full bytes include line endings. The three historical mixed-line-ending files
remain verbatim, with their existing `-text` attributes. The check rejects
missing/extra protected files, changed manifests, altered bytes/EOL and wrong
httpx/psycopg/pypdf versions. CI needs no production token, normal PostgreSQL or
local RAW files.

## Deployment boundary

The local deployment was completed through a separately approved procedure
with a full backup/restore trial and three append-only inserts. The source
change has no startup DDL, migrations or automatic activation/import.
**Merging this code does not authorize production APPLY in any environment.**
A new active instance needs its own explicit target-bound authorization and
data backup; an offline fixture cannot replace runtime approval or data.

F2, diagnostic prototypes and local data/credentials are outside this release.
The functional tests and independent byte check cover different properties;
passing pytest alone is not proof of runtime integrity.

## Validation

Validation uses a clean Git export of the exact proposed PR, without F2 or
local RAW: backend pytest, frontend Vitest, TypeScript, production build, all
PostgreSQL integration steps, and integrity/mutation checks. It also checks
the approved runtime bytes after checkout with Windows `core.autocrlf=true`.
CI repeats verification on the actual PR checkout. Results and any transient
test failures are included in the PR description.

The prior optional Overview-explanations test once exceeded its default wait
under parallel load. Its assertions and timeouts remain unchanged.
