"""Explicit market universe, separate from macro series and MCI components."""
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "market_assets.yaml"


def load_market_assets() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as stream:
        assets = yaml.safe_load(stream)
    if not isinstance(assets, dict) or not assets:
        raise RuntimeError("Market assets config must be a nonempty mapping.")
    for key, metadata in assets.items():
        if not isinstance(key, str) or not key.isalnum() or not isinstance(metadata, dict):
            raise RuntimeError("Invalid market asset config.")
        if any(not metadata.get(field) for field in ("name", "asset_class", "provider", "source", "source_organization", "source_url", "frequency", "unit", "attribution")):
            raise RuntimeError(f"Incomplete market metadata: {key}")
        if metadata["provider"] != "fred" or metadata["frequency"] != "daily":
            raise RuntimeError("Market v1 supports the FRED daily provider only.")
    return assets
