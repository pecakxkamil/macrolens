"""Descriptive comparisons of latest-stored MacroLens histories."""

import math
from datetime import date
from typing import Optional

from app.analytics import history, relationship_sources as sources


FREQUENCY_ORDER = {"daily": 0, "weekly": 1, "monthly": 2, "quarterly": 3}
MIN_CORRELATION_OBSERVATIONS = 3
ALIGNMENT_METHODOLOGY = (
    "Use the lowest frequency among selected series. Group observations by ISO day, "
    "ISO week, calendar month, or calendar quarter at that frequency; select the "
    "latest dated non-null observation per series in each period. Keep periods with "
    "at least one value. Pearson correlation uses only periods with values for both "
    "series; fewer than three pairs or zero variance returns null. Indexed values "
    "use 100 at the first shared period only for eligible positive levels. No observations are carried from earlier periods or interpolated."
)


class InvalidRelationshipSelectionError(ValueError):
    """Raised when the same history is selected twice or a third feature lacks a series."""


def _period(observation_date: date, frequency: str) -> str:
    if frequency == "daily":
        return observation_date.isoformat()
    if frequency == "weekly":
        year, week, _ = observation_date.isocalendar()
        return f"{year}-W{week:02d}"
    if frequency == "monthly":
        return observation_date.strftime("%Y-%m")
    return f"{observation_date.year}-Q{(observation_date.month - 1) // 3 + 1}"


def _finite_value(value) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _latest_by_period(observations: list[dict], frequency: str) -> dict:
    latest = {}
    for observation in observations:
        value = _finite_value(observation["value"])
        if value is None:
            continue
        observation_date = observation["observation_date"]
        period = _period(observation_date, frequency)
        current = latest.get(period)
        if current is None or observation_date > current["observation_date"]:
            latest[period] = {"observation_date": observation_date, "value": value}
    return latest


def _pearson(pairs: list[tuple[float, float]]) -> Optional[float]:
    if len(pairs) < MIN_CORRELATION_OBSERVATIONS:
        return None
    left_mean = sum(left for left, _ in pairs) / len(pairs)
    right_mean = sum(right for _, right in pairs) / len(pairs)
    covariance = sum((left - left_mean) * (right - right_mean) for left, right in pairs)
    left_variance = sum((left - left_mean) ** 2 for left, _ in pairs)
    right_variance = sum((right - right_mean) ** 2 for _, right in pairs)
    if left_variance <= 0 or right_variance <= 0:
        return None
    return max(-1.0, min(1.0, covariance / math.sqrt(left_variance * right_variance)))


def _load(series_id: str, feature_name: Optional[str], start_date: Optional[date], end_date: Optional[date]) -> dict:
    if series_id in sources.asset_config():
        return sources.load_asset(series_id, start_date, end_date)
    loaded = (history.load_feature_history(series_id, feature_name, start_date, end_date)
              if feature_name is not None else history.load_series_history(series_id, start_date, end_date))
    loaded = {**loaded, "source_kind": "macro", "excluded_observation_count": 0}
    if feature_name is not None:
        safe, excluded = sources.calendar_safe_points(series_id, feature_name, loaded["frequency"], loaded["observations"])
        loaded.update(observations=safe, excluded_observation_count=excluded)
    return loaded


def compare_histories(
    left_series: str,
    right_series: str,
    left_feature: Optional[str] = None,
    right_feature: Optional[str] = None,
    third_series: Optional[str] = None,
    third_feature: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Align two or three configured histories without altering stored observations."""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise history.InvalidDateRangeError("start_date must be on or before end_date.")
    if third_feature is not None and third_series is None:
        raise InvalidRelationshipSelectionError("third_feature requires third_series.")

    requests = [("left", left_series, left_feature), ("right", right_series, right_feature)]
    if third_series is not None:
        requests.append(("third", third_series, third_feature))
    histories = [(series_id, None if feature_name == "level" else feature_name) for _, series_id, feature_name in requests]
    if len(set(histories)) != len(histories):
        raise InvalidRelationshipSelectionError("Select distinct histories.")

    for _, series, feature in requests:
        sources.validate_source(series, feature)

    loaded = {key: _load(series_id, feature_name, start_date, end_date)
              for key, series_id, feature_name in requests}
    frequency = max((item["frequency"] for item in loaded.values()), key=FREQUENCY_ORDER.__getitem__)
    aligned = {key: _latest_by_period(item["observations"], frequency) for key, item in loaded.items()}
    periods = sorted(set().union(*(set(items) for items in aligned.values())))
    rows = [{"period": period, **{key: aligned[key].get(period) for key in loaded}} for period in periods]

    eligible = all((feature in (None, "level") and loaded[key]["unit"] != "percent" and series not in ("CFNAI", "NFCI", "ISM_MANUFACTURING_PMI", "ISM_SERVICES_PMI")) for key, series, feature in requests)
    positive = all(point["value"] > 0 for values in aligned.values() for point in values.values())
    baseline = next((row for row in rows if all(row[key] is not None for key in loaded)), None) if eligible and positive else None
    indexing = {"available": baseline is not None, "reason": None if baseline else "Indexed comparison requires positive levels and a shared period. Growth rates, rates, changes and diffusion/financial conditions indices are excluded."}
    for row in rows:
        for key in loaded:
            item = row[key]
            if item is not None:
                item["normalized_value"] = (
                    100 * item["value"] / baseline[key]["value"] if baseline is not None else None
                )

    keys = list(loaded)
    pair_keys = [(keys[0], keys[1])]
    if len(keys) == 3:
        pair_keys.extend(((keys[0], keys[2]), (keys[1], keys[2])))
    comparisons = []
    for left_key, right_key in pair_keys:
        paired = [row for row in rows if row[left_key] is not None and row[right_key] is not None]
        pairs = [(row[left_key]["value"], row[right_key]["value"]) for row in paired]
        comparisons.append({
            "left_key": left_key,
            "right_key": right_key,
            "overlapping_observation_count": len(pairs),
            "correlation": _pearson(pairs),
            "first_pair_period": paired[0]["period"] if paired else None,
            "last_pair_period": paired[-1]["period"] if paired else None,
        })

    return {
        "history_type": history.HISTORY_TYPE,
        "indexing": indexing,
        "feature_policy": sources.GAP_POLICY,
        "start_date": start_date,
        "end_date": end_date,
        "comparison_frequency": frequency,
        "alignment_methodology": ALIGNMENT_METHODOLOGY,
        "normalization_base_period": baseline["period"] if baseline is not None else None,
        "indicators": [{
            "key": key,
            "series_id": item["series_id"],
            "feature_name": item.get("feature_name"),
            "name": item["name"],
            "short_name": item.get("short_name"),
            "frequency": item["frequency"],
            "source_kind": item.get("source_kind", "macro"),
            "source_url": item.get("source_url", f"https://fred.stlouisfed.org/series/{series_id}"),
            "attribution": item.get("attribution"),
            "excluded_observation_count": item.get("excluded_observation_count", 0),
            "unit": {"percent": "percentage points", "index": "index points"}.get(item["unit"], item["unit"]) if feature_name and feature_name.startswith("change_") else item["unit"] if feature_name is None or feature_name == "level" else (
                "percent" if feature_name in ("yoy", "mom", "qoq", "qoq_annualized", "annualized_3m")
                else item["unit"]
            ),
        } for key, series_id, feature_name in requests for item in [loaded[key]]],
        "observations": rows,
        "overlapping_observation_count": comparisons[0]["overlapping_observation_count"],
        "correlation": comparisons[0]["correlation"],
        "comparisons": comparisons,
    }
