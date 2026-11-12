"""Mutation tests only touch disposable copies, never the running checkout."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import io
from importlib import metadata
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import check_forecast_integrity as guard


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.baseline = guard.load_baseline()
        self.temp = TemporaryDirectory(prefix="macrolens-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in self.baseline["files"]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(guard.ROOT / name, target)

    def errors(self, reader=None):
        return guard.verify(self.root, self.baseline, reader)

    def test_approved_checkout_and_real_installed_versions(self):
        self.assertEqual(self.errors(), [])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(guard.main(["--root", str(self.root)]), 0)

    def test_changed_protected_file(self):
        path = self.root / "app/forecast_f1.py"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertTrue(any("SHA-256 mismatch: app/forecast_f1.py" in e for e in self.errors()))

    def test_crlf_to_lf_is_a_byte_mismatch(self):
        path = self.root / "config/forecast_f1_dispatch_policy.json"
        raw = path.read_bytes()
        self.assertIn(b"\r\n", raw)
        path.write_bytes(raw.replace(b"\r\n", b"\n"))
        self.assertTrue(any("SHA-256 mismatch" in e and "dispatch_policy" in e for e in self.errors()))

    def test_mixed_endings_are_preserved_verbatim(self):
        path = self.root / "app/ingestion/request_budget.py"
        raw = path.read_bytes()
        self.assertIn(b"\r\n", raw)
        self.assertNotEqual(raw.count(b"\r\n"), raw.count(b"\n"))
        path.write_bytes(raw.replace(b"\r\n", b"\n"))
        self.assertTrue(any("SHA-256 mismatch: app/ingestion/request_budget.py" in e for e in self.errors()))

    def test_missing_file(self):
        (self.root / "app/forecast_f1.py").unlink()
        self.assertIn("Missing protected source path: app/forecast_f1.py", self.errors())

    def test_unexpected_protected_path(self):
        (self.root / "app/unreviewed.py").write_text("pass\n")
        self.assertIn("Unexpected protected source path: app/unreviewed.py", self.errors())

    def test_changed_runtime_manifest(self):
        path = self.root / guard.SPEC
        spec = json.loads(path.read_text())
        spec["paths"].remove("app/forecast_f1.py")
        path.write_text(json.dumps(spec), encoding="utf-8")
        errors = self.errors()
        self.assertTrue(any("SHA-256 mismatch" in e and guard.SPEC in e for e in errors))
        self.assertIn("Runtime manifest path list differs from the approved 161 paths", errors)

    def test_invalid_runtime_manifest(self):
        (self.root / guard.SPEC).write_text("not JSON")
        self.assertIn("Missing or invalid runtime manifest: " + guard.SPEC, self.errors())

    def test_wrong_library_version_and_cli_failure(self):
        actual = metadata.version
        def wrong(name):
            return "0.0.0" if name == "psycopg" else actual(name)
        self.assertTrue(any("Library version mismatch: psycopg" in e for e in self.errors(wrong)))
        with patch.object(guard.metadata, "version", wrong), redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(guard.main(["--root", str(self.root)]), 1)
        self.assertIn("Library version mismatch: psycopg", errors.getvalue())

    def test_missing_library(self):
        def absent(name):
            raise metadata.PackageNotFoundError(name)
        self.assertEqual(sum(e.startswith("Missing library:") for e in self.errors(absent)), 3)

    def test_baseline_cannot_adopt_current_files(self):
        value = copy.deepcopy(self.baseline)
        value["files"]["app/forecast_f1.py"] = "0" * 64
        path = self.root / "tampered-baseline.json"
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "previously approved map"):
            guard.load_baseline(path)

    def test_duplicate_baseline_keys_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text('{"format_version": 1, "format_version": 1}')
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            guard.load_baseline(path)


    def test_historical_v3_baseline_remains_explicit_and_pinned(self):
        historical = guard.load_baseline(authorization_version=3)
        self.assertEqual(len(historical["files"]), 156)
        self.assertEqual(historical["approved_plan_sha256"], guard.APPROVALS[3][0])
        self.assertEqual(self.baseline["authorization_version"], 4)
        with self.assertRaisesRegex(ValueError, "authorization version"):
            guard.load_baseline(guard.BASELINES[3])

    def test_explicit_v3_cannot_accept_v4_checkout(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(guard.main(["--root", str(self.root), "--authorization-version", "3"]), 1)

    def test_all_three_mixed_files_reject_eol_normalization(self):
        for name in ("app/analytics/overview_refresh_store.py", "app/database/overview_refresh.sql", "app/ingestion/request_budget.py"):
            with self.subTest(path=name):
                path = self.root / name
                raw = path.read_bytes()
                self.assertIn(b"\r\n", raw)
                self.assertNotEqual(raw.count(b"\r\n"), raw.count(b"\n"))
                path.write_bytes(raw.replace(b"\r\n", b"\n"))
                self.assertTrue(any("SHA-256 mismatch: " + name in e for e in self.errors()))
                path.write_bytes(raw)

    def test_baseline_cannot_switch_approved_plan_or_version(self):
        for key, value in (("approved_plan_sha256", "0" * 64), ("authorization_version", 3)):
            with self.subTest(field=key):
                changed = copy.deepcopy(self.baseline)
                changed[key] = value
                path = self.root / "foreign-baseline.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    guard.load_baseline(path)


if __name__ == "__main__":
    unittest.main()
