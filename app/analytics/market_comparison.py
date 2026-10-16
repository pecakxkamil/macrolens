"""Descriptive monthly MCI / market comparison. No model or strategy logic."""
from datetime import date
from typing import Optional
from app.analytics import history, macro_conditions_index as mci, point_in_time_mci as pit
from app.analytics.relationships import _finite_value, _pearson, MIN_CORRELATION_OBSERVATIONS
from app.database.connection import get_connection
from app.market_assets import load_market_assets


class InvalidMarketComparisonError(ValueError):
    pass


def select_assets(assets: str, config: dict) -> list:
    requested = assets.split(",")
    if not requested or len(requested) != len(set(requested)) or any(key not in config for key in requested):
        raise InvalidMarketComparisonError("Select distinct configured assets: " + ", ".join(config))
    return [key for key in config if key in requested]


def load_market_history(series_id: str, cutoff: date) -> list:
    if series_id not in load_market_assets():
        raise InvalidMarketComparisonError("Unknown market asset.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(history.SERIES_HISTORY_SQL, (series_id, None, None, cutoff, cutoff))
            return [{"observation_date": str(day), "value": value} for day, value in cursor.fetchall()]
    finally:
        connection.close()


def _prices(observations: list) -> list:
    # Source-missing dates do not become zero prices. Use the latest available
    # finite positive price and expose its actual date, even across holidays.
    dated = {}
    for observation in observations:
        value = _finite_value(observation["value"])
        if value is not None and value > 0:
            dated[str(observation["observation_date"])] = value
    return sorted(dated.items())


def build_comparison(macro_rows: list, asset_histories: dict, metadata: dict,
                     start_date: Optional[date] = None, end_date: Optional[date] = None,
                     macro_history_type: str = "point_in_time", mode: str = "indexed") -> dict:
    history._validate_date_range(start_date, end_date)
    if macro_history_type not in ("point_in_time", "current_vintage") or mode not in ("actual", "indexed"):
        raise InvalidMarketComparisonError("Invalid macro history type or display mode.")
    cutoff = min(end_date or date.today(), date.today())
    by_month = {}
    for row in macro_rows:
        day = str(row.get("as_of_date") or row["observation_date"])
        observed = date.fromisoformat(day)
        if observed > cutoff or mci._month_end(observed) != observed:
            continue
        by_month[day] = _finite_value(row.get("mci"))
    prices = {key: _prices(rows) for key, rows in asset_histories.items()}
    pointers = {key: 0 for key in prices}
    latest = {key: None for key in prices}
    rows, previous = [], None
    for day, macro_value in sorted(by_month.items()):
        row = {"as_of_date": day, "mci": macro_value, "mci_change": None}
        consecutive = previous is not None and mci._shift_month(mci._month(date.fromisoformat(previous["as_of_date"])), 1) == mci._month(date.fromisoformat(day))
        if consecutive and macro_value is not None and previous["mci"] is not None:
            row["mci_change"] = macro_value - previous["mci"]
        for key, values in prices.items():
            while pointers[key] < len(values) and values[pointers[key]][0] <= day:
                latest[key] = values[pointers[key]]
                pointers[key] += 1
            selected = latest[key]
            row[key] = selected[1] if selected else None
            row[key + "_observation_date"] = selected[0] if selected else None
            prior = previous[key] if consecutive else None
            row[key + "_return_1m"] = 100 * (row[key] / prior - 1) if prior and row[key] is not None else None
        rows.append(row)
        previous = row
    shared = [row for row in rows if row["mci"] is not None and all(row[key] is not None for key in prices)]
    overlap_start = shared[0]["as_of_date"] if shared else None
    overlap_end = shared[-1]["as_of_date"] if shared else None
    display_start = str(start_date) if start_date else overlap_start
    rows = [row for row in rows if display_start is None or row["as_of_date"] >= display_start]
    base = next((row for row in rows if row["mci"] is not None and all(row[key] is not None for key in prices)), None)
    base_values = {key: base[key] for key in prices} if base else {}
    for row in rows:
        for key in prices:
            row[key + "_indexed"] = 100 * row[key] / base_values[key] if base and row[key] is not None and row["as_of_date"] >= base["as_of_date"] else None
    statistics = []
    for key in prices:
        relations = {}
        for macro_key in ("mci", "mci_change"):
            pairs = [(row[macro_key], row[key + "_return_1m"]) for row in rows
                     if row[macro_key] is not None and row[key + "_return_1m"] is not None]
            relations[macro_key] = {"overlapping_observations": len(pairs), "correlation": _pearson(pairs),
                "variable_definitions": {"macro": "MCI month-end level (0-100)" if macro_key == "mci" else "MCI month-end level minus previous month-end level (points)",
                                         "market": "100 * (aligned monthly price / previous aligned monthly price - 1)"}}
        statistics.append({"asset_id": key, **relations})
    return {"methodology_version": "v1", "macro_history_type": macro_history_type, "market_history_type": "latest_stored_observations",
        "frequency": "monthly", "alignment": "last_observation_on_or_before_month_end", "mode": mode,
        "start_date": str(start_date) if start_date else None, "end_date": str(end_date) if end_date else None,
        "status": "ready" if base else "insufficient_overlap", "base_date": base["as_of_date"] if base else None,
        "base_values": base_values, "rows": rows, "statistics": statistics,
        "minimum_correlation_observations": MIN_CORRELATION_OBSERVATIONS,
        "available_overlap_start": overlap_start, "available_overlap_end": overlap_end,
        "message": None if base else "No common date with MCI and all selected asset prices. Select another range or refresh market data.",
        "series": [{"series_id": "MCI", "name": "Point-in-time MCI" if macro_history_type == "point_in_time" else "Current-vintage MCI", "unit": "0-100", "source": "MacroLens", "first_observation": min(by_month, default=None), "last_observation": max(by_month, default=None)},
                   *[{"series_id": key, **metadata[key], "first_observation": prices[key][0][0] if prices[key] else None,
                      "last_observation": next((day for day, _ in reversed(prices[key]) if day <= str(cutoff)), None)} for key in prices]],
        "limitations": "Descriptive historical comparison only. Correlation does not imply causation or predictive power. PIT macro availability is date-level, not intraday. Market observations are latest stored history, not an ALFRED vintage backfill. Nasdaq price-index changes exclude dividends; Coinbase represents one venue. Different axes have different units."}


def compare_market(assets: str = "NASDAQCOM", start_date: Optional[date] = None,
                   end_date: Optional[date] = None, macro_history_type: str = "point_in_time", mode: str = "indexed") -> dict:
    config = load_market_assets()
    selected = select_assets(assets, config)
    history._validate_date_range(start_date, end_date)
    if macro_history_type not in ("point_in_time", "current_vintage") or mode not in ("actual", "indexed"):
        raise InvalidMarketComparisonError("Invalid macro history type or display mode.")
    cutoff = min(date.today(), end_date) if end_date else date.today()
    macro = pit.get_history(end_date=cutoff) if macro_history_type == "point_in_time" else mci.get_index_history(end_date=cutoff)
    loaded = {key: load_market_history(key, cutoff) for key in selected}
    return build_comparison(macro["observations"], loaded, config, start_date, end_date, macro_history_type, mode)
