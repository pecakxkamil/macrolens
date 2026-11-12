"""Verify approved F1 V3/V4/V5 checkouts without importing app code or accessing SQL."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
BASELINES = {v: Path(__file__).with_name(f"forecast_f1_v{v}_baseline.json") for v in (3, 4, 5)}
BASELINE = BASELINES[5]
SPEC = "config/forecast_f1_runtime_manifest_v2.json"
APPROVALS = {
    3: ("374e93e3c7f21cf232db989e0532045c073328f71b2e4c3e5b3da3265499e2ad",
        "541d41bf1a7156f1f9d3e90d9f037428118e0c19790309c9309f60be38823fb8", 156),
    4: ("ebfe454621a598db1745690e1d94b0d35227add8916f2823a35f9595280e689c",
        "90af2f8758569aa1ac0667855827b0b67167313ea21ec0f4cc05073cf0c23cbb", 161),
    5: ("9b2265be70c2efc13845ed3c38c7aea1f8481b08c569726aaf4cb736164b51a4",
        "386fb5b3c266e6faa90dca2c748a0cef6969e7666b15d272635415e87c904dad", 163),
}
LIBRARIES = ("httpx", "psycopg", "pypdf")
SUFFIXES = {".py", ".sql", ".json", ".yaml", ".yml"}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def load_baseline(path=None, authorization_version=5):
    if authorization_version not in APPROVALS:
        raise ValueError("Unapproved authorization version")
    plan_sha, artifacts_sha, file_count = APPROVALS[authorization_version]
    value = read_json(path if path is not None else BASELINES[authorization_version])
    keys = {"format_version", "authorization_version", "approved_plan_sha256",
            "approved_artifacts_sha256", "files", "libraries"}
    if set(value) != keys or value["format_version"] != 1 or value["authorization_version"] != authorization_version:
        raise ValueError("Unknown baseline format or authorization version")
    if value["approved_plan_sha256"] != plan_sha:
        raise ValueError("Baseline is not tied to the explicitly approved deployment plan")
    files, libraries = value["files"], value["libraries"]
    if not isinstance(files, dict) or len(files) != file_count or SPEC not in files:
        raise ValueError(f"Baseline must contain exactly {file_count} approved source paths")
    if not isinstance(libraries, dict) or set(libraries) != set(LIBRARIES):
        raise ValueError("Baseline must contain exactly three approved libraries")
    for name, checksum in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or "\\" in name
                or not (name == "requirements.txt" or path.parts[0] in ("app", "config"))):
            raise ValueError("Invalid protected path: " + name)
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid SHA-256 for: " + name)
    artifacts = {**files, **{name + "_version": libraries[name] for name in LIBRARIES}}
    if value["approved_artifacts_sha256"] != artifacts_sha or digest(artifacts) != artifacts_sha:
        raise ValueError("Baseline artifact map differs from the previously approved map")
    return value


def verify(root, baseline, version_reader=None):
    root = Path(root).resolve()
    errors = []
    expected = set(baseline["files"])
    inventory = {"requirements.txt"}
    for folder in ("app", "config"):
        for path in (root / folder).rglob("*"):
            if path.is_file() and path.suffix in SUFFIXES and "__pycache__" not in path.parts:
                inventory.add(path.relative_to(root).as_posix())
    for name in sorted(inventory - expected):
        errors.append("Unexpected protected source path: " + name)
    for name in sorted(expected - inventory):
        errors.append("Missing protected source path: " + name)

    for name, checksum in baseline["files"].items():
        path = root / name
        if not path.is_file():
            if name in inventory:
                errors.append("Missing protected source path: " + name)
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append("Protected path must be a regular file inside checkout: " + name)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != checksum:
            errors.append("SHA-256 mismatch: " + name + " (expected " + checksum + ", got " + actual + ")")

    try:
        spec = read_json(root / SPEC)
        if set(spec) != {"version", "scope", "paths", "versions"} or spec["version"] != 2:
            errors.append("Unknown protected runtime manifest format")
        paths = spec["paths"]
        if paths != sorted(expected) or len(paths) != len(set(paths)):
            errors.append(f"Runtime manifest path list differs from the approved {len(expected)} paths")
        if spec["versions"] != list(LIBRARIES):
            errors.append("Runtime manifest library list differs from the approved three libraries")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("Missing or invalid runtime manifest: " + SPEC)

    version_reader = version_reader or metadata.version
    for name, expected_version in baseline["libraries"].items():
        try:
            actual = version_reader(name)
        except metadata.PackageNotFoundError:
            errors.append("Missing library: " + name + " (expected " + expected_version + ")")
            continue
        if actual != expected_version:
            errors.append("Library version mismatch: " + name + " (expected " + expected_version + ", got " + str(actual) + ")")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Checkout to verify; baseline stays fixed")
    parser.add_argument("--authorization-version", type=int, choices=(3, 4, 5), default=5,
                        help="Explicit historical V3/V4 verification; CI always selects V5")
    args = parser.parse_args(argv)
    label = f"F1 V{args.authorization_version} integrity"
    try:
        baseline = load_baseline(authorization_version=args.authorization_version)
        errors = verify(args.root, baseline)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(label + " ERROR: " + str(error), file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(label + " ERROR: " + error, file=sys.stderr)
        return 1
    count = len(baseline["files"])
    print(f"{label} OK: {count}/{count} exact file hashes, 3/3 library versions ({count+3}/{count+3}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
