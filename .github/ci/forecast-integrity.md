# Forecast F1 V3 integrity check

`forecast_f1_v3_baseline.json` is a static projection of the previously
approved BLS deployment plan, canonical SHA-256:
`374e93e3c7f21cf232db989e0532045c073328f71b2e4c3e5b3da3265499e2ad`.
The canonical digest of its original 159-entry artifact map is
`541d41bf1a7156f1f9d3e90d9f037428118e0c19790309c9309f60be38823fb8`.
These identities are also checked independently in the verifier.

Provenance: [approved deployment preparation](../../docs/audits/macrolens-bls-production-upgrade-preparation-2026-11-06.md)
and [completed activation](../../docs/audits/macrolens-bls-normal-activation-2026-11-06.md).
The baseline copies only source-path/hash pairs and three library versions
from that approved plan. It contains no database identity, token, policy,
document, receipt, private data or original deployment plan.

The verifier uses only the standard library. It does not import application
code, connect to PostgreSQL, fetch providers, initialize anything or load
`data/raw`. It hashes bytes without normalizing line endings, compares the
protected runtime manifest and its Python/SQL/JSON/YAML inventory, and reads
the installed versions of httpx, psycopg and pypdf via package metadata.
The inventory boundary matches the authorized manifest's app/config suffixes
plus requirements.txt; caches and unrelated frontend/integrations are outside it.

The dedicated CI job installs exactly the approved three versions in its
own runner. Existing functional jobs keep their existing dependency policy
and PostgreSQL test service. Their success is separate from the 159-artifact
integrity result. No production authorization is performed on any runner.

Run locally in an environment with the approved libraries:

```powershell
.venv/Scripts/python.exe .github/ci/check_forecast_integrity.py
.venv/Scripts/python.exe -m unittest discover -s .github/ci -p test_forecast_integrity.py -v
```

The mutation tests use disposable copies. Any mismatch exits nonzero and
names the missing/unexpected path, byte checksum, manifest inconsistency
or installed library version. This verifies the actual result of checkout,
including the three mixed-line-ending files, rather than trusting Git settings.

Never regenerate this baseline from the files being tested to make CI pass.
A future approved backend/library change needs an independently reviewed
replacement baseline and explicit review of these constants. This is a
reviewed CI gate, not a cryptographic signature: changes to the verifier,
workflow and baseline themselves still require human review. Passing this
check does not grant SQL rights, activate F1 or authorize production APPLY.
