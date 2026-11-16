# MacroLens continuous integration

## Current CI on main

The source of truth is [the workflow](../.github/workflows/ci.yml) and the
[run for the exact commit](https://github.com/pecakxkamil/macrolens/actions/workflows/ci.yml).
It runs on pushes to `main`, pull requests targeting `main`, and manual dispatch.
Four independent jobs must finish successfully; queued or running checks are not passes.

| Job | Runtime | Checks |
|---|---|---|
| Backend tests | Ubuntu 24.04, Python 3.12 | Full pytest suite with external HTTP/SQL guards |
| Frontend tests and build | Ubuntu 24.04, Node 22 | Locked npm install, full Vitest suite with network guard, TypeScript and Vite build |
| PostgreSQL integration tests | Ubuntu 24.04, disposable PostgreSQL 17 | 20 validation stages, including revisions, rollback, Earnings and F1 activation/recovery |
| Forecast F1 V6 integrity | Ubuntu 24.04, Python 3.12 | 22 checker tests and 165 exact file hashes + 3 pinned library versions = 168 artifacts |

Integrity checking uses the independently approved static V6 baseline, not a
freshly generated hash map. Historical V3/V4/V5 maps remain available.
See [the integrity contract](../.github/ci/forecast-integrity.md) for provenance,
checkout line endings and commands. A passing functional suite alone does not
prove byte integrity or authorize a production instance.

Unit tests use fixtures/mocks. The PostgreSQL job creates its own disposable
databases on a loopback-only runner service; activation tests operate there,
never on the normal MacroLens database. CI needs no production token, provider
credentials or `data/raw`. It does not deploy, import live provider data, or
perform production APPLY. The integrity job only needs the checkout and
`httpx==0.28.1`, `psycopg[binary]==3.2.13`, `pypdf==6.21.2`.

For local commands see [README](../README.md#testy-i-ci) and
[local development](local-development.md#validation-without-real-providers).
Do not aim the PostgreSQL validation scripts at an existing personal database.
No local full-suite rerun is required for documentation-only changes.

## Historical setup record — 27 October 2026

The sections below describe the initial two-job implementation and its original
validation. Their package versions, case counts, lack of a PostgreSQL service,
and first-run instructions are historical, not the current CI contract above.

## Audit before implementation — 27 October 2026

The starting checkout was clean at `8e8a490`, synchronized with `origin/main`.
There was no `.github/workflows` directory, pytest configuration or shared
`tests/conftest.py`. No existing workflow was replaced.

- Backend: 704 pytest cases under `tests/`. Tests use synthetic observations,
  fake connections/cursors, memory refresh stores, monkeypatches and HTTPX
  `MockTransport`. FastAPI's `TestClient` calls the app in process.
- Frontend: 523 cases across 22 files, using Vitest 2.1.9, Testing Library and
  jsdom. Existing tests stub `fetch`; `frontend/src/test/setup.ts` loads jest-dom.
  Vite 6.4.3 and TypeScript 5.9.3 provide the existing `tsc && vite build` command.
  `package-lock.json` is committed; no npm dependency was changed for CI.
- The developer environment uses Python 3.9.13, Node 20.9.0 and npm 10.1.0.
  Backend requirements are unpinned; examples of installed local packages were
  pytest 8.4.2, pandas 2.3.3, FastAPI 0.128.8 and psycopg 3.2.13.
- PostgreSQL 17 in `docker-compose.yml` serves the running application, but the
  existing test suite does not require it. No CI database, schema application,
  ingestion, provider credentials or saved macro dataset is required.

## Workflow

`.github/workflows/ci.yml` defines **MacroLens CI**:

| Check | Runtime | Commands |
| --- | --- | --- |
| Backend tests | Ubuntu 24.04, Python 3.12 | `python -m pip install -r requirements.txt`, `python -m pytest -q` |
| Frontend tests and build | Ubuntu 24.04, Node 22 | `npm ci --no-audit --no-fund`, `npm test`, `npm run build` |

It runs on pushes to `main`, pull requests targeting `main` and manual
`workflow_dispatch`. Both jobs run independently. Newer runs cancel obsolete
runs for the same branch/PR. Each job has a 15-minute execution cap; individual
test timeouts and existing test cases are unchanged. There are no path filters,
test exclusions or `continue-on-error` steps. A failing test prevents a successful
job; the frontend build runs after its tests succeed.

The workflow has read-only repository contents permission and does not persist
checkout credentials. Official checkout/setup actions are pinned by commit SHA.
Pip/npm download caches use the requirements/lockfile; runtime data and `.env`
are not uploaded. No secrets, paid service, deployment or provider ingestion is
configured. Standard GitHub-hosted runners are
[free for public repositories](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Offline test boundaries

`pytest.ini` sets `testpaths = tests`, preserving all existing backend cases and
preventing pytest from collecting ignored diagnostic copies under `data/raw`.

`tests/conftest.py` installs guards before collection, disables dotenv loading,
clears the provider key and sets dummy database settings. Real HTTPX transports,
Python DNS/socket connections and native psycopg connection entry points fail
the run. Mock transports, fake database objects and in-process API tests remain
usable. A caught access error or a background attempt still makes the test/session
fail. The narrow Windows exception permits only the standard library's internal
loopback `socketpair` used by asyncio; it does not allow general localhost traffic.

The frontend test step preloads `.github/ci/no-network.cjs` through `NODE_OPTIONS`.
It blocks real `fetch`, DNS, TCP and TLS entry points, including in test workers.
Mocks remain usable. A caught network exception still sets a failing exit status.
This preload is not included in the application or production build.

Dependency installation requires package-registry access. The guards apply to
tests, not dependency downloads, and are test isolation rather than a sandbox
for hostile dependency code. They do not inspect or validate live provider data.
No application server or PostgreSQL process is started by CI. If real SQL
integration tests are added later, they need a separately designed disposable
PostgreSQL service/schema; do not point them at a developer/production database.

## Local reproduction

From the repository root, with the project's dependencies installed:

```sh
python -m pytest -q
cd frontend
npm ci --no-audit --no-fund
NODE_OPTIONS=--require=../.github/ci/no-network.cjs npm test
npm run build
cd ..
git diff --check
```

On PowerShell, use `.\.venv\Scripts\python.exe -m pytest -q` for the backend.
To enable the same frontend guard without overwriting existing shell options:

```powershell
Set-Location frontend
$ciOriginalNodeOptions = $env:NODE_OPTIONS
try {
    $env:NODE_OPTIONS = '--require=../.github/ci/no-network.cjs'
    npm test
} finally {
    $env:NODE_OPTIONS = $ciOriginalNodeOptions
}
npm run build
Set-Location ..
git diff --check
```

An optional local workflow syntax check is `actionlint .github/workflows/ci.yml`.
This validates YAML, Actions expressions and step structure, without starting
GitHub jobs. See the official
[Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python),
[Node](https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs)
and [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
guides for the underlying GitHub configuration.

## Local validation recorded on 27 October 2026

- Full Windows suites with offline guards: **704 backend / 523 frontend passed**.
- Fresh Linux containers: **Python 3.12.16 / Node 22.23.4 / npm 10.9.9**.
  Dependencies were installed from the existing requirements and npm lockfile.
  Containers received a clean code copy without `.env`, `.git`, `node_modules`,
  local database contents, derived caches or RAW captures. They had no published
  ports, database mounts or provider credentials. After dependency installation,
  their Docker network was detached before testing/building.
- Linux full suites: **704 backend / 523 frontend passed** with guards and no
  external network. Production build/type-check passed, with the existing main
  bundle warning (**507.49 kB**, unchanged 500 kB threshold).
- Fresh Python resolution included pytest 9.1.1, pandas 3.1.0, FastAPI 0.162.0,
  HTTPX 0.28.1 and psycopg 3.3.6. FastAPI/Starlette emits an HTTPX TestClient
  deprecation warning; it was retained, not filtered out. Requirements remain
  unpinned, so future package releases can change resolution and need review.
- Deliberate HTTP, DNS and database probes failed as expected, including a caught
  request during backend test collection. Node fetch/TCP/DNS probes also failed
  despite catching the error; an offline control process succeeded. Probe files
  and logs remain ignored under `data/raw/`.
- **actionlint 1.7.12 passed**. Its official release archive was SHA-256 checked.
  Official action tag SHAs were checked against their upstream repositories.
- No test was removed/skipped, no test timeout was increased, and no application,
  observation, feature, MCI/PIT calculation or database volume was changed.

These were local results at the end of the initial configuration stage, which
did not commit or push. A subsequent user instruction authorized publishing the
workflow and verifying GitHub Actions. The run for the published commit is the
authoritative remote result; the local checks above do not establish its status.

## First GitHub verification after a separately authorized push

1. Ensure GitHub Actions is enabled in repository settings. No API-key secrets
   need to be created. Fork PRs may require a maintainer to approve the run.
2. Push the workflow in a separately authorized change, or open a PR targeting
   `main`. Once the workflow exists on `main`, it can also be started from
   **Actions → MacroLens CI → Run workflow**.
3. Open the run for the exact commit. Verify both **Backend tests** and
   **Frontend tests and build** succeed, and inspect the production-build step.
   A pending/cancelled run is not a passing check.
4. If merge enforcement is wanted, add both check names to the `main` branch
   ruleset after their first run. The workflow alone does not prevent direct
   pushes or merges. This task does not change repository rules/settings.

GitHub runner provisioning, action/cache downloads and repository permissions
remain to be confirmed by that first remote run. Local Docker validation is a
Linux compatibility/offline check, not an emulator of the GitHub control plane.
