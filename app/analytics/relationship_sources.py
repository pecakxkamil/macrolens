"""Configured source adapters and calendar checks for Relationships only."""
import math
from bisect import bisect_right
from datetime import date, timedelta
from app.analytics import history, series_catalog
from app.analytics.features import FEATURES_BY_SERIES, METHODOLOGY_VERSION, YOY_LAG_BY_SERIES
from app.analytics.compute_features import load_point_in_time_snapshot
from app.database.connection import get_connection
from app.database.sync_series import load_series_config
from app.local_ism import SERIES
from app.market_assets import load_market_assets

MARKET_IDS = {"NASDAQCOM", "CBBTCUSD"}
GAP_POLICY = "Stored row-based features are shown only where all required source periods exist in their computation snapshot. Unverified points are excluded; no feature is recalculated here."
WINDOW_LAGS = {"mom": 1, "qoq": 1, "qoq_annualized": 1, "annualized_3m": 3,
    "monthly_change": 1, "monthly_change_ma_3m": 3, "monthly_change_ma_6m": 6,
    "change_3m": 3, "change_6m": 6, "change_4w": 4, "change_13w": 13,
    "moving_average_3m": 2, "moving_average_4w": 3, "moving_average_13w": 12}


def asset_config():
    return {sid: item for sid, item in load_market_assets().items() if sid in MARKET_IDS}


def validate_source(series, feature):
    assets, macro = asset_config(), {**load_series_config(), **SERIES}
    if series in assets:
        if feature is not None:
            raise history.UnsupportedFeatureError("Market assets support stored prices only.")
    elif series not in macro:
        raise history.UnknownSeriesError("Unknown configured relationship source.")
    elif feature is not None and (feature not in macro[series].get("transformations", ()) or feature not in FEATURES_BY_SERIES.get(series, ())):
        raise history.UnsupportedFeatureError("Unsupported configured relationship transformation.")


def list_sources():
    macro = series_catalog.list_active_series()["series"]
    config = {**load_series_config(), **SERIES}
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT series_id, feature_name FROM computed_features WHERE methodology_version = %s AND feature_value IS NOT NULL AND series_id = ANY(%s)", (METHODOLOGY_VERSION, [row["series_id"] for row in macro]))
            stored = set(cursor.fetchall())
    finally:
        connection.close()
    sources = [{**row, "source_kind": "macro", "features": [f for f in config[row["series_id"]].get("transformations", ()) if f in FEATURES_BY_SERIES.get(row["series_id"], ()) and (row["series_id"], f) in stored]} for row in macro]
    sources.extend({"series_id": sid, "name": item["name"], "short_name": item["name"], "category": "market", "frequency": item["frequency"], "unit": item["unit"], "features": [], "source_kind": "asset", "source_url": item["source_url"], "attribution": item["attribution"]} for sid, item in asset_config().items())
    return {"sources": sources, "history_type": history.HISTORY_TYPE, "feature_policy": GAP_POLICY}


def load_asset(series, start, end):
    meta = asset_config()[series]
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(history.SERIES_HISTORY_SQL, (series, start, start, end, end))
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {"series_id": series, **meta, "short_name": meta["name"], "source_kind": "asset", "history_type": history.HISTORY_TYPE,
        "observations": [{"observation_date": day, "value": value} for day, value in rows]}


def _earlier(day, frequency, offset):
    if frequency == "weekly":
        return day - timedelta(weeks=offset)
    months = offset * (3 if frequency == "quarterly" else 1)
    ordinal = day.year * 12 + day.month - 1 - months
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def calendar_safe_points(series, feature, frequency, observations):
    if feature == "level":
        return observations, 0
    lag = YOY_LAG_BY_SERIES.get(series) if feature == "yoy" else WINDOW_LAGS.get(feature)
    if lag is None or frequency not in ("weekly", "monthly", "quarterly"):
        return [], len(observations)
    cache, safe = {}, []
    connection = None
    try:
        for point in observations:
            as_of = point.get("feature_as_of_date")
            if not as_of:
                continue
            as_of = date.fromisoformat(str(as_of))
            if as_of not in cache:
                if connection is None:
                    connection = get_connection()
                # This is the exact existing loader used to compute stored v1 features.
                frame = load_point_in_time_snapshot(connection, series, as_of)
                cache[as_of] = sorted({date.fromisoformat(str(day)[:10]) for day, value in zip(frame["observation_date"], frame["value"]) if value is not None and math.isfinite(float(value))})
            day = date.fromisoformat(str(point["observation_date"]))
            required = {_earlier(day, frequency, n) for n in range(lag + 1)}
            end = bisect_right(cache[as_of], day)
            if day == _earlier(day, frequency, 0) and cache[as_of][max(0, end - lag - 1):end] == sorted(required):
                safe.append(point)
    finally:
        if connection is not None:
            connection.close()
    return safe, len(observations) - len(safe)
