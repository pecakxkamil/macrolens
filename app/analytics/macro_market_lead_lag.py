"""Calendar-aligned descriptive MCI changes versus market returns."""
from bisect import bisect_right
from datetime import date
from typing import Optional
from app.analytics import history, macro_conditions_index as mci, point_in_time_mci as pit
from app.analytics import market_comparison as market
from app.analytics.relationships import _finite_value, _pearson
from app.market_assets import load_market_assets

MAX_PRICE_AGE_DAYS = 7
LAGS = range(-6, 7)
LAG_CONVENTION = "Corr(delta_MCI_t, R_asset_(t+k)): positive k means MCI change precedes return; negative k means return precedes MCI change; zero is same-month."


def _months(first, last):
    month = mci._month(first)
    while month <= mci._month(last):
        yield month
        month = mci._shift_month(month, 1)


def validate(start_date, end_date, macro_history_type, rolling_window):
    history._validate_date_range(start_date, end_date)
    if macro_history_type not in ("point_in_time", "current_vintage") or rolling_window not in (24, 36):
        raise market.InvalidMarketComparisonError("Use point_in_time or current_vintage history and a 24 or 36 calendar-month window.")


def build_analysis(macro_rows: list, asset_histories: dict, metadata: dict,
                   start_date: Optional[date] = None, end_date: Optional[date] = None,
                   macro_history_type: str = "point_in_time", rolling_window: int = 24,
                   available_through: Optional[date] = None) -> dict:
    validate(start_date, end_date, macro_history_type, rolling_window)
    market.select_assets(",".join(asset_histories), metadata)
    available = min(available_through or date.today(), date.today())
    # Only completed calendar months; market return months need not have an MCI row.
    last = mci._month(available)
    if mci._month_end(last) > available:
        last = mci._shift_month(last, -1)
    macro = {}
    for row in macro_rows:
        day = date.fromisoformat(str(row.get("as_of_date") or row["observation_date"]))
        if day == mci._month_end(day) and day <= available:
            macro[mci._month(day)] = _finite_value(row.get("mci"))
    first = mci._shift_month(min(macro, default=last), -7)
    months = list(_months(first, last)) if macro else []
    anchor_end = min(end_date or available, available)
    anchors = [month for month in months if month >= min(macro, default=last) and (start_date is None or mci._month_end(month) >= start_date)
               and mci._month_end(month) <= anchor_end and month <= max(macro, default=last)]
    changes = {month: macro[month] - macro[mci._shift_month(month, -1)]
               if macro.get(month) is not None and macro.get(mci._shift_month(month, -1)) is not None else None
               for month in months}
    assets = []
    for asset_id in metadata:
        if asset_id not in asset_histories:
            continue
        prices = market._prices(asset_histories[asset_id])
        days = [day for day, _ in prices]
        aligned = {}
        for month in months:
            end = mci._month_end(month)
            index = bisect_right(days, str(end)) - 1
            selected = prices[index] if index >= 0 else None
            age = (end - date.fromisoformat(selected[0])).days if selected else None
            aligned[month] = {"value": selected[1] if selected and age <= MAX_PRICE_AGE_DAYS else None,
                              "observation_date": selected[0] if selected else None, "age_days": age}
        returns = {}
        for month in months:
            current = aligned[month]["value"]
            prior = aligned.get(mci._shift_month(month, -1), {}).get("value")
            returns[month] = 100 * (current / prior - 1) if current is not None and prior is not None else None
        lag_results = []
        for lag in LAGS:
            pairs_by_month = {}
            for month in months:
                target = mci._shift_month(month, lag)
                change, asset_return = changes[month], returns.get(target)
                if change is not None and asset_return is not None:
                    pairs_by_month[month] = {"anchor_date": str(mci._month_end(month)),
                        "return_date": str(mci._month_end(target)), "mci_change": change,
                        "asset_return": asset_return, "asset_id": asset_id, "asset_name": metadata[asset_id]["name"],
                        "price_observation_date": aligned[target]["observation_date"],
                        "previous_price_observation_date": aligned[mci._shift_month(target, -1)]["observation_date"]}
            pairs = [pairs_by_month[month] for month in anchors if month in pairs_by_month]
            rolling = []
            for month in anchors:
                window = list(_months(mci._shift_month(month, -(rolling_window - 1)), month))
                valid = [pairs_by_month[day] for day in window if day in pairs_by_month]
                rolling.append({"anchor_date": str(mci._month_end(month)), "valid_pairs": len(valid),
                    "correlation": _pearson([(p["mci_change"], p["asset_return"]) for p in valid]) if len(valid) == rolling_window else None})
            lag_results.append({"lag": lag, "correlation": _pearson([(p["mci_change"], p["asset_return"]) for p in pairs]),
                "n": len(pairs), "first_anchor_date": pairs[0]["anchor_date"] if pairs else None,
                "last_anchor_date": pairs[-1]["anchor_date"] if pairs else None,
                "pairs": pairs, "rolling": rolling, "missing_anchor_count": len(anchors) - len(pairs)})
        assets.append({"asset_id": asset_id, "name": metadata[asset_id]["name"], "lags": lag_results,
            "missing_price_dates": [str(mci._month_end(day)) for day in months if aligned[day]["value"] is None]})
    return {"methodology_version": "v1", "macro_history_type": macro_history_type,
        "lag_convention": LAG_CONVENTION, "units": {"mci_change": "index points", "asset_return": "percent", "lag": "calendar months"},
        "rolling_window": rolling_window, "maximum_price_age_days": MAX_PRICE_AGE_DAYS,
        "start_date": str(start_date) if start_date else None, "end_date": str(end_date) if end_date else None,
        "available_through": str(available), "anchor_count": len(anchors), "assets": assets,
        "coverage": {"first_anchor_date": str(mci._month_end(anchors[0])) if anchors else None,
                     "last_anchor_date": str(mci._month_end(anchors[-1])) if anchors else None,
                     "missing_mci_change_dates": [str(mci._month_end(day)) for day in anchors if changes[day] is None]},
        "boundary_policy": "Only MCI anchor t is restricted to the reporting range. Returns at t+k may lie outside it. Prior history supplies deltas, returns and rolling windows; positive lags use later available completed months, never fabricated future data.",
        "rolling_policy": "All 24/36 calendar-month pairs must be valid; otherwise correlation is null. Positive-lag rolling points use returns after the anchor and are retrospective.",
        "limitations": "Descriptive, not causal or predictive. Same-month correlation is not a prediction. Multiple testing across 13 lags and unstable correlations require caution. PIT availability is date-level, not intraday. Market history is latest stored data."}


def analyze(assets: str = "NASDAQCOM,CBBTCUSD", start_date: Optional[date] = None,
            end_date: Optional[date] = None, macro_history_type: str = "point_in_time", rolling_window: int = 24) -> dict:
    config = load_market_assets()
    selected = market.select_assets(assets, config)
    validate(start_date, end_date, macro_history_type, rolling_window)
    # Full prior macro history supports rolling windows at the reporting boundary.
    cutoff = min(end_date or date.today(), date.today())
    available = min(mci._month_end(mci._shift_month(mci._month(cutoff), 6)), date.today())
    macro = pit.get_history(end_date=cutoff) if macro_history_type == "point_in_time" else mci.get_index_history(end_date=cutoff)
    loaded = {key: market.load_market_history(key, available) for key in selected}
    result = build_analysis(macro["observations"], loaded, config, start_date, end_date, macro_history_type, rolling_window, available)
    result["data_loading_window"] = {"start_date": None, "end_date": str(available), "policy": "All stored prior history and up to six later months, capped at today; incomplete months excluded."}
    return result
