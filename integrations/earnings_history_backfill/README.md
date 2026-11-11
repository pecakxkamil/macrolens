# Reviewed E2E Previous extension

This is an explicit operation using the existing `earnings_historical_reports`
store, its immutable SQL guard, fiscal predecessor reader, validation and
deterministic approved insertion path. It is never imported by normal API
startup, polling or Calendar GET. It does not initialize a schema.

The seven reviewed records are ARM Q1 FY2027, QCOM Q3 FY2026, PANW Q4 FY2026
SNOW Q2 FY2027, NVDA Q4 FY2026, AMZN Q1 2026 and INTC Q1 2026. All values use consolidated quarterly USD revenue and
reported US GAAP diluted EPS (six pairs). Intel has revenue only: its attributable-to-Intel EPS methodology cannot be relabeled to the existing history total-EPS constraint. ARM uses ordinary shares; the others common
shares. Negative GAAP EPS is preserved. Source units remain in the ledger.

The existing `app/earnings_history.py` module is loaded into a separate private
module object with this operation's reviewed ledger. The live module and its
original ledger are untouched. Prepared records then use the existing E2E
approved INSERT function. Isolated-import guards are not removed. This keeps
the active F1 V2 backend manifest and the Earnings monitor unchanged.

Run from the repository root. Prepare/plan/verify are read-only. APPLY requires
a new explicit approval for the exact full plan hash and target, unchanged
operation/backend/ledger fingerprints, and a verified complete backup/restore.

```powershell
.venv/Scripts/python.exe -m integrations.earnings_history_backfill prepare --identity path/to/identity.json --backup path/to/backup.json --out path/to/plan.json
.venv/Scripts/python.exe -m integrations.earnings_history_backfill plan --plan path/to/plan.json --backup path/to/backup.json --out path/to/rechecked.json
.venv/Scripts/python.exe -m integrations.earnings_history_backfill apply --plan path/to/plan.json --backup path/to/backup.json --confirm-target localhost:5432/macrolens --confirm-plan FULL_APPROVED_HASH --out path/to/receipt.json
.venv/Scripts/python.exe -m integrations.earnings_history_backfill verify --plan path/to/plan.json --out path/to/verified.json
```

Do not reuse an E2E/F1 approval. On a changed target, schema, baseline, ledger
or artifact, stop and prepare a new plan for separate approval. Existing
historical periods are rejected by prepare; this operation cannot revise them.
One transaction adds only seven reports (13 metrics). A SQL failure rolls back the batch.
Idempotent retry verifies the original rows and imported payloads without new
timestamps. There is no automatic post-commit restore or deletion.
