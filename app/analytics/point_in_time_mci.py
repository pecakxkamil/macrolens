"""Date-level PIT MCI v1 reconstructed from immutable ALFRED vintages."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi.encoders import jsonable_encoder

from app.analytics import history, macro_conditions_index as mci, point_in_time
from app.analytics.features import calculate_features
from app.ingestion.backfill_vintages import MCI_SERIES

FEATURES = {series: tuple(dict.fromkeys(feature for spec in mci.COMPONENTS
                                     if spec.series_id == series for feature in spec.features))
            for series in MCI_SERIES}
DEPENDENCIES = {
    "monthly_change_ma_3m": tuple(range(4)), "monthly_change_ma_6m": tuple(range(7)),
    "change_3m": (0, 3), "moving_average_4w": tuple(range(4)),
    "moving_average_13w": tuple(range(13)), "yoy": (0, 12),
    "qoq_annualized": (0, 1), "moving_average_3m": tuple(range(3)),
    "annualized_3m": (0, 3), "level": (0,),
}
WEEKLY_SERIES = {"ICSA", "NFCI"}
CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "derived" / "mci_point_in_time_v1.json"


def methodology_metadata() -> dict:
    result = mci.methodology_metadata()
    result.update({
        "history_type": "point_in_time",
        "alignment": {
            "monthly_weekly": "Latest finite feature actually available at the as-of date. Monthly source periods expire after 3 months; weekly after 35 days.",
            "gdp": "Only actually known quarters whose period has ended. GDP expires 6 months after its quarter-start observation; revisions known at T recompute its score.",
            "calendar": "Historical rows are month-end as-of dates. Availability is date-level, not intraday.",
        },
        "current_selection": "Latest fully backfilled completed month-end; null scores remain visible when components are unavailable.",
        "limitation": "Point-in-time uses only data vintages available by each historical month-end. ALFRED realtime dates establish date-level availability, not precise publication times. Designed to reduce look-ahead bias; not a validated trading or forecasting model.",
        "feature_reconstruction": "Existing pure v1 feature formulas run on the latest-known ALFRED observations at T. Missing calendar periods remain null. No computed_features table is read.",
    })
    result["normalization"] = {**result["normalization"], "reference": "Expanding component features reconstructed from the history known at T; reference observations never use future vintages."}
    return result


def reconstruct_features(series_id: str, rows: list, as_of_date: date) -> tuple:
    """Use the shared pure formulas; return the dated raw dependency grid too."""
    known = point_in_time.select_as_of(rows, as_of_date)
    if not known:
        return pd.DataFrame(columns=["observation_date", "feature_name", "feature_value"]), []
    by_date = {item["observation_date"]: item for item in known}
    start, end = sorted(by_date)[0], sorted(by_date)[-1]
    if series_id in WEEKLY_SERIES:
        weekday = pd.Timestamp(start).day_name()[:3].upper()
        frequency = f"W-{weekday}"
    else:
        frequency = "QS" if series_id == "GDPC1" else "MS"
    # Explicit gaps prevent shift/rolling from silently compressing missing periods.
    dates = pd.date_range(start, end, freq=frequency)
    grid = []
    for observed in dates:
        key = observed.date().isoformat()
        item = by_date.get(key)
        grid.append({"observation_date": key, "vintage_date": item["vintage_date"] if item else None,
                     "value": mci._finite(item["value"]) if item else None,
                     "realtime_end": item.get("realtime_end") if item else None})
    frame = pd.DataFrame([{"observation_date": item["observation_date"], "value": item["value"]} for item in grid])
    return calculate_features(series_id, frame, FEATURES[series_id]), grid


def build_as_of(known: dict, as_of_date: date, coverage: dict, audit: bool = False, cache: Optional[dict] = None) -> dict:
    histories, grids = {}, {}
    cache = cache if cache is not None else {}
    for series in MCI_SERIES:
        rows = list(known.get(series, {}).values()) if isinstance(known.get(series), dict) else known.get(series, [])
        selected = point_in_time.select_as_of(rows, as_of_date)
        signature = tuple((item["observation_date"], item["vintage_date"], item["value"]) for item in selected)
        if series not in cache or cache[series][0] != signature:
            features, grid = reconstruct_features(series, selected, as_of_date)
            cache[series] = signature, features, grid
        _, features, grids[series] = cache[series]
        for feature in FEATURES[series]:
            observations = [
                {"observation_date": str(row.observation_date), "value": row.feature_value,
                 "feature_as_of_date": str(as_of_date)}
                for row in features.itertuples() if row.feature_name == feature
            ]
            histories[(series, feature)] = {"observations": observations}

    domains = {}
    for domain, name in mci.DOMAIN_NAMES.items():
        specs = [spec for spec in mci.COMPONENTS if spec.domain == domain]
        readings = []
        for spec in specs:
            # Shared monthly grouping may include the current month in an exact-date
            # audit. Every input has already been constrained to actual availability T.
            events = mci._events(spec, histories, mci._month_end(mci._month(as_of_date)))
            scored = mci._score_events(spec, events)
            latest = max(scored) if scored else None
            grid = grids[spec.series_id]
            current = scored[latest] if latest else None
            if current:
                observed = mci._date(current["source_observation_date"])
                age = (as_of_date.year - observed.year) * 12 + as_of_date.month - observed.month
                expired = ((as_of_date - observed).days > 35 if spec.series_id in WEEKLY_SERIES
                           else age >= 6 if spec.quarterly else age > 3)
                if expired:
                    current = None
            reading = mci._component_reading(spec, {mci._month(as_of_date): current} if current else {},
                                             mci._month(as_of_date), 1 / len(specs))
            dependencies = []
            if current:
                index = next(i for i, item in enumerate(grid) if item["observation_date"] == current["source_observation_date"])
                offsets = set(offset for feature in spec.features for offset in DEPENDENCIES[feature])
                dependencies = [grid[index - offset].copy() for offset in sorted(offsets, reverse=True) if index >= offset]
                reading["carried_forward"] = mci._month(observed) < mci._month(as_of_date)
            reading["vintage_dates_used"] = sorted({item["vintage_date"] for item in dependencies if item["vintage_date"]})
            reading["raw_observations_used"] = dependencies
            verified = coverage.get(spec.series_id, "") >= str(as_of_date)
            if not verified:
                reading.update(score=None, domain_contribution=None, mci_contribution=None, status="coverage_unverified")
            if audit:
                reading["normalization_reference"] = [
                    {"observation_date": event["source_observation_date"], "value": event["raw_value"]}
                    for _, event in sorted(events.items())
                ]
            readings.append(reading)
        score = sum(item["domain_contribution"] for item in readings) if all(
            item["score"] is not None for item in readings) else None
        vintage_dates = [value for item in readings for value in item["vintage_dates_used"]]
        domains[domain] = {
            "name": name, "score": score, "weight": mci.DOMAIN_WEIGHT,
            "contribution": score * mci.DOMAIN_WEIGHT if score is not None else None,
            "as_of_date": max(vintage_dates) if vintage_dates else None, "components": readings,
        }
    total = sum(item["contribution"] for item in domains.values()) if all(
        item["score"] is not None for item in domains.values()) else None
    result = {
        "as_of_date": str(as_of_date), "observation_date": str(as_of_date),
        "latest_evaluated_month": str(as_of_date), "mci": total, "domains": domains,
        "component_as_of_dates": {key: item["as_of_date"] for key, item in domains.items()},
    }
    if audit:
        result["series_inputs"] = grids
    return result


def _first_valid_as_of_date(observations: list, cutoff: date) -> Optional[str]:
    """Derive coverage from full history before applying the display start range."""
    return min((row["as_of_date"] for row in observations
                if row["as_of_date"] <= str(cutoff) and mci._finite(row.get("mci")) is not None), default=None)


def _coverage(rows: list, verified: dict) -> dict:
    by_series = {}
    for series in MCI_SERIES:
        subset = [row for row in rows if row["series_id"] == series]
        by_series[series] = {
            "first_vintage_date": min((row["vintage_date"] for row in subset), default=None),
            "first_observation_date": min((row["observation_date"] for row in subset), default=None),
            "backfilled_through": verified.get(series), "stored_vintage_rows": len(subset),
        }
    missing = [series for series, item in by_series.items() if not item["first_vintage_date"] or not item["backfilled_through"]]
    return {
        "series": by_series, "missing_series": missing,
        "backfilled_through": min(verified.values()) if not missing else None,
        "first_valid_as_of_date": None,
    }


def build_history(rows: list, verified: dict, cutoff: date) -> dict:
    coverage = _coverage(rows, verified)
    observations = []
    if not coverage["missing_series"]:
        first = max(item["first_vintage_date"] for item in coverage["series"].values())
        month = mci._month(mci._date(first))
        end = min(cutoff, mci._date(coverage["backfilled_through"]))
        stream = sorted(rows, key=lambda item: (item["vintage_date"], item["series_id"], item["observation_date"]))
        pointer, known, cache = 0, {series: {} for series in MCI_SERIES}, {}
        while mci._month_end(month) <= end:
            as_of = mci._month_end(month)
            while pointer < len(stream) and stream[pointer]["vintage_date"] <= str(as_of):
                item = stream[pointer]
                known[item["series_id"]][item["observation_date"]] = item
                pointer += 1
            result = build_as_of(known, as_of, verified, cache=cache)
            observations.append({
                "as_of_date": str(as_of), "observation_date": str(as_of), "mci": result["mci"],
                **{key: value["score"] for key, value in result["domains"].items()},
                "component_availability": {
                    item["key"]: item["status"] for domain in result["domains"].values() for item in domain["components"]
                },
            })
            month = mci._shift_month(month, 1)
    coverage["first_valid_as_of_date"] = _first_valid_as_of_date(observations, cutoff)
    return {**methodology_metadata(), "as_of_date": str(cutoff), "coverage": coverage, "observations": observations}


def get_history(start_date: Optional[date] = None, end_date: Optional[date] = None, rebuild: bool = False) -> dict:
    history._validate_date_range(start_date, end_date)
    cutoff = min(date.today(), end_date) if end_date else date.today()
    signature = point_in_time.load_backfill_signature()
    result = None
    if not rebuild and CACHE_PATH.exists():
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as stream:
                candidate = json.load(stream)
            if (candidate.get("history_type") == "point_in_time"
                    and candidate.get("methodology_version") == "v1"
                    and candidate.get("source_signature") == signature
                    and candidate.get("cache_complete_history")
                    and candidate.get("as_of_date", "") >= str(cutoff)):
                result = candidate
        except (OSError, ValueError):
            pass
    if result is None:
        rows, verified = point_in_time.load_vintage_panel(cutoff)
        result = build_history(rows, verified, cutoff)
    result["coverage"] = {**result.get("coverage", {}),
                          "first_valid_as_of_date": _first_valid_as_of_date(result["observations"], cutoff)}
    result["source_signature"] = signature
    result["cache_complete_history"] = start_date is None
    result["as_of_date"] = str(cutoff)
    result["observations"] = [row for row in result["observations"]
                              if (start_date is None or row["as_of_date"] >= str(start_date))
                              and (end_date is None or row["as_of_date"] <= str(end_date))]
    result.update(start_date=str(start_date) if start_date else None, end_date=str(end_date) if end_date else None)
    return result


def _concise_audit(result: dict) -> dict:
    """Keep exact feature dependencies and rank counts; full grids stay internal."""
    result.pop("series_inputs", None)
    for domain in result["domains"].values():
        for component in domain["components"]:
            reference = component.pop("normalization_reference", [])
            value = component["raw_value"]
            if component["orientation"] == "target_distance":
                component["normalization_summary"] = {
                    "method": "target_distance", "reference_observation_count": 0,
                    "reference_percent": mci.INFLATION_REFERENCE,
                    "zero_score_distance_pp": mci.INFLATION_ZERO_DISTANCE,
                    "distance_pp": abs(value - mci.INFLATION_REFERENCE) if value is not None else None,
                }
            else:
                # A missing/expired component has no scored reference distribution.
                values = [row["value"] for row in reference] if value is not None else []
                component["normalization_summary"] = {
                    "method": "expanding_midrank_percentile",
                    "orientation": component["orientation"],
                    "reference_observation_count": len(values),
                    "minimum": min(values, default=None), "maximum": max(values, default=None),
                    "below_value_count": sum(item < value for item in values) if value is not None else None,
                    "equal_value_count": sum(item == value for item in values) if value is not None else None,
                    "above_value_count": sum(item > value for item in values) if value is not None else None,
                }
    return result


def get_audit(as_of_date: date) -> dict:
    if as_of_date > date.today():
        raise history.InvalidDateRangeError("as_of_date must not be in the future.")
    rows, verified = point_in_time.load_vintage_panel(as_of_date)
    known = {series: [row for row in rows if row["series_id"] == series] for series in MCI_SERIES}
    coverage = _coverage(rows, verified)
    coverage["first_valid_as_of_date"] = get_history(end_date=as_of_date)["coverage"]["first_valid_as_of_date"]
    return {**methodology_metadata(), **_concise_audit(build_as_of(known, as_of_date, verified, audit=True)),
            "coverage": coverage}


def get_current() -> dict:
    rows, verified = point_in_time.load_vintage_panel(date.today())
    coverage = _coverage(rows, verified)
    end = min(date.today(), mci._date(coverage["backfilled_through"])) if coverage["backfilled_through"] else date.today()
    month = mci._month(end)
    as_of = mci._month_end(month)
    if as_of > end:
        as_of = mci._month_end(mci._shift_month(month, -1))
    known = {series: [row for row in rows if row["series_id"] == series] for series in MCI_SERIES}
    coverage["first_valid_as_of_date"] = get_history(end_date=as_of)["coverage"]["first_valid_as_of_date"]
    return {**methodology_metadata(), **build_as_of(known, as_of, verified), "coverage": coverage}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild/export PIT MCI history from locally stored ALFRED rows.")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--output", type=Path, default=CACHE_PATH)
    args = parser.parse_args()
    try:
        result = get_history(args.start_date, args.end_date, rebuild=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as stream:
            json.dump(jsonable_encoder(result), stream, indent=2)
            stream.write("\n")
        print(json.dumps({"output": str(args.output), "month_end_rows": len(result["observations"]),
                          "coverage_start": result["coverage"]["first_valid_as_of_date"],
                          "missing_series": result["coverage"]["missing_series"]}))
        return 0
    except Exception as error:
        print(f"PIT MCI rebuild failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

