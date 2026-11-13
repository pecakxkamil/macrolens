# Forecast F1 V5: reviewed historical financial readings

V5 binds five financial readings to independently reviewed publication columns.
For the H.15 publication dated November 10, 2026, the four daily measures use
November 9 observations and November 6 as the preceding comparable business
observation. The November 5 PMMS reading uses the dated November 5 / October 29
weekly pair. No new importer or latest-observation fallback is introduced.

| Measure | Actual / Previous (%) |
|---|---:|
| DFF | 3.88 / 3.88 |
| DGS2 | 4.56 / 4.51 |
| DGS10 | 4.88 / 4.86 |
| DFII10 | 2.66 / 2.63 |
| MORTGAGE30US | 7.18 / 7.24 |

Other events remain null without publication/period evidence. PMMS has no
invented publication hour. Previous is a documented comparable observation,
including weekend/holiday boundaries, and absent data never becomes zero.
Numerically higher/lower/equal changes remain green/red/neutral. Current
snapshots retain explicit provenance and are not presented as intraday first
prints. Conflicting publisher versions are rejected.

The runtime authorization extends the immutable V1-V4 chain with V5, an explicit
append-only revision. Existing forecasts, freezes, CPI contracts, Employment,
shared BLS budget and Earnings behavior are preserved. File cutover has exact
before/after guards and a reviewed rollback path. No startup DDL, migrations or
automatic authorization/import is introduced. The local activation was completed
through a separate approved procedure; merging code does not authorize production
APPLY or initialization in another environment.

CI trusts only the previously approved static map:

- Plan SHA-256: `9b2265be70c2efc13845ed3c38c7aea1f8481b08c569726aaf4cb736164b51a4`.
- Artifact map SHA-256: `386fb5b3c266e6faa90dca2c748a0cef6969e7666b15d272635415e87c904dad`.
- 163 exact files plus httpx 0.28.1, psycopg 3.2.13 and pypdf 6.21.2: 166 artifacts.

The public baseline contains only paths, hashes and library versions from that
approved map. It is never generated from the checkout under test. Historical V3
and V4 baselines remain pinned and explicitly selectable. Tests reject changed
files/EOL (including mixed endings), missing/extra inventory, altered manifests,
wrong libraries, version downgrade and a substituted/rehashed V5 map. No normal
database, production token or RAW documents are needed by the static checker.

F2, diagnostic prototypes, private activation reports, target-bound plans, tokens,
backup/restore material and operational receipts remain outside this release.
Restoring an active instance requires separately authorized data/authorization
material; fixtures are not replacements for it.

The known EconomyBrief explanation-button timeout at high parallel load remains
a validation limitation. A repeat with fewer workers does not establish a permanent
fix, and no assertion or timeout is weakened by this release.

CI adds one narrow `.gitattributes` rule for the reviewed public evidence fixture:
`tests/fixtures/financial_publication_columns.json text eol=lf`. This preserves its
original SHA under Windows autocrlf without normalizing evidence in the test.
The production commit retains all 21 approved delivery files; the separate CI
commit adds only this checkout rule to that attributes file. None of the 163
runtime artifact hashes changes. The deployed local attributes file remains the
approved activation version; exact deployment procedures must use their reviewed
delivery archive and validate all delivery hashes, rather than assuming any Git
checkout is an authorization to rerun the existing target-bound plan.
