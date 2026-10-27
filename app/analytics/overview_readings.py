"""Bounded current-vintage comparisons for the curated Overview readings."""
from datetime import date, timedelta
from app.analytics.history import load_series_history
from app.analytics.features import METHODOLOGY_VERSION
from app.analytics.relationships import _finite_value
from app.database.connection import get_connection

# Domain, component, source, stored transformation, label, frequency, units, delta units.
READINGS = (
    ("labor", "payrolls", "PAYEMS", "monthly_change", "Payroll monthly change", "monthly", "thousands", "thousands"),
    ("labor", "unemployment", "UNRATE", "level", "Unemployment rate", "monthly", "percent", "percentage points"),
    ("labor", "initial_claims", "ICSA", "raw", "Initial jobless claims", "weekly", "claims", "claims"),
    ("labor", "job_openings", "JTSJOL", "level", "JOLTS job openings", "monthly", "thousands of openings", "thousands of openings"),
    ("labor", "average_hourly_earnings", "CES0500000003", "mom", "Average hourly earnings MoM", "monthly", "percent", "percentage points"),
    ("inflation", "headline_cpi", "CPIAUCSL", "mom", "CPI MoM", "monthly", "percent", "percentage points"),
    ("inflation", "core_cpi", "CPILFESL", "mom", "Core CPI MoM", "monthly", "percent", "percentage points"),
    ("inflation", "core_pce", "PCEPILFE", "mom", "Core PCE MoM", "monthly", "percent", "percentage points"),
    ("inflation", "producer_ppi", "PPIFIS", "mom", "Producer inflation PPI MoM", "monthly", "percent", "percentage points"),
    ("growth", "real_gdp", "GDPC1", "qoq_annualized", "Real GDP QoQ annualized", "quarterly", "percent", "percentage points"),
    ("growth", "manufacturing_pmi", "ISM_MANUFACTURING_PMI", "raw", "Manufacturing PMI", "monthly", "index", "index points"),
    ("growth", "services_pmi", "ISM_SERVICES_PMI", "raw", "Services PMI", "monthly", "index", "index points"),
    ("growth", "industrial_production", "INDPRO", "mom", "Industrial production MoM", "monthly", "percent", "percentage points"),
    ("consumer", "real_consumption", "PCEC96", "mom", "Real consumption MoM", "monthly", "percent", "percentage points"),
    ("consumer", "real_disposable_income", "DSPIC96", "mom", "Real disposable income MoM", "monthly", "percent", "percentage points"),
    ("consumer", "retail_sales", "RSAFS", "mom", "Nominal retail sales MoM", "monthly", "percent", "percentage points"),
    ("housing", "housing_starts", "HOUST", "level", "Housing starts", "monthly", "thousands SAAR", "thousands SAAR"),
    ("housing", "building_permits", "PERMIT", "level", "Building permits", "monthly", "thousands SAAR", "thousands SAAR"),
    ("housing", "mortgage_rate", "MORTGAGE30US", "level", "30Y mortgage rate", "weekly", "percent", "percentage points"),
    ("financial_conditions", "yield_curve_2s10s", "DGS2 / DGS10", "spread", "10Y minus 2Y Treasury spread", "daily", "percentage points", "percentage points"),
    ("financial_conditions", "nfci", "NFCI", "level", "NFCI", "weekly", "index", "index points"),
)


def offset_period(observed, frequency, periods):
    if frequency == "weekly":
        return observed - timedelta(weeks=periods)
    ordinal = observed.year * 12 + observed.month - 1 - periods * (3 if frequency == "quarterly" else 1)
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def compare_overview_readings(rows):
    """Monthly/quarterly/weekly gaps are never compressed; daily offsets count available observations."""
    # SQL joins YoY at each primary observation date. Pure callers may also
    # supply existing five-column feature-history rows for the same series.
    normalized = [row[:5] for row in rows]
    normalized.extend((row[0], "yoy", row[2], row[5], row[6]) for row in rows if len(row) == 7 and row[5] is not None)
    rows = normalized
    result = []
    for domain, component, series, feature, label, frequency, unit, change_unit in READINGS:
        available = {str(day): {"value": _finite_value(value), "feature_as_of_date": str(as_of) if as_of is not None else None}
                     for sid, fname, day, as_of, value in rows if sid == series and fname == feature}
        finite_dates = sorted(day for day, row in available.items() if row["value"] is not None)
        latest = finite_dates[-1] if finite_dates else None
        def target(periods):
            if not latest:
                return None
            if frequency == "daily":
                return finite_dates[-1 - periods] if len(finite_dates) > periods else None
            return str(offset_period(date.fromisoformat(latest), frequency, periods))
        def point(day):
            if day in available and available[day]["value"] is not None:
                return {"observation_date": day, **available[day]}
            return None
        previous_day, earlier_day = target(1), target(3)
        current, previous, earlier = point(latest), point(previous_day), point(earlier_day)
        def context_point(context_feature, day):
            matches = [row for row in rows if row[0] == series and row[1] == context_feature and str(row[2]) == day]
            if not matches or _finite_value(matches[-1][4]) is None:
                return None
            return {"observation_date": day, "feature_as_of_date": str(matches[-1][3]) if matches[-1][3] is not None else None, "value": _finite_value(matches[-1][4])}
        context = {"current": context_point("yoy", latest), "previous": context_point("yoy", previous_day), "three_periods_ago": context_point("yoy", earlier_day)} if feature == "mom" and series != "PPIFIS" else None
        interval = {"daily": "available observation", "weekly": "calendar week", "monthly": "calendar month", "quarterly": "calendar quarter"}[frequency]
        result.append({"domain": domain, "component": component, "series_id": series, "feature_name": feature,
                       "label": label, "frequency": frequency, "unit": unit, "change_unit": change_unit,
                       "current": current, "previous": previous, "three_periods_ago": earlier, "context_yoy": context,
                       "context_moving_average_4w": context_point("moving_average_4w", latest) if series == "ICSA" and feature == "raw" else None,
                       "expected_previous_observation_date": previous_day,
                       "expected_three_periods_ago_date": earlier_day,
                       "latest_stored_observation_date": max(available, default=None),
                       "change_type": f"Difference from previous {interval}",
                       "change": current["value"] - previous["value"] if current and previous else None})
    return result


def load_reading_comparisons(today):
    sources = [(spec[2], spec[3], spec[5]) for spec in READINGS if spec[3] not in ("spread", "raw")]
    sources += [(spec[2], "yoy", "monthly") for spec in READINGS if spec[3] == "mom" and spec[2] != "PPIFIS"]
    sources += [("ICSA", "moving_average_4w", "weekly")]
    sources += [("DGS2", "level", "daily"), ("DGS10", "level", "daily")]
    placeholders = ",".join(["(%s,%s,%s)"] * len(sources))
    # One query selects current-vintage values before bounding the result. The
    # curve uses same-date yields, exactly as in Financial Conditions; it is not
    # formed by subtracting independently selected latest observations.
    sql = f"""
        WITH requested(series_id, feature_name, frequency) AS (VALUES {placeholders}),
        current_features AS MATERIALIZED (
            SELECT DISTINCT ON (f.series_id, f.feature_name, f.observation_date)
                   f.series_id, f.feature_name, f.observation_date, f.as_of_date, f.feature_value, r.frequency
            FROM computed_features f
            JOIN requested r ON r.series_id = f.series_id AND r.feature_name = f.feature_name
            WHERE f.methodology_version = %s AND f.observation_date <= %s
            ORDER BY f.series_id, f.feature_name, f.observation_date, as_of_date DESC, computed_at DESC, id DESC
        ),
        histories AS (
            SELECT * FROM current_features WHERE series_id NOT IN ('DGS2', 'DGS10') AND feature_name != 'yoy'
            UNION ALL
            SELECT 'DGS2 / DGS10', 'spread', a.observation_date, GREATEST(a.as_of_date, b.as_of_date),
                   b.feature_value - a.feature_value, 'daily'
            FROM current_features a JOIN current_features b ON a.observation_date = b.observation_date
            WHERE a.series_id = 'DGS2' AND b.series_id = 'DGS10'
        ),
        marked AS (
            SELECT *, feature_value IS NOT NULL AND feature_value::text NOT IN ('NaN', 'Infinity', '-Infinity') AS finite
            FROM histories
        ),
        bounded AS (
            SELECT *, MAX(observation_date) FILTER (WHERE finite) OVER w AS latest,
                   MAX(observation_date) OVER w AS latest_stored,
                   COUNT(*) FILTER (WHERE finite) OVER (
                       PARTITION BY series_id, feature_name ORDER BY observation_date DESC
                       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS available_rank
            FROM marked WINDOW w AS (PARTITION BY series_id, feature_name)
        )
        SELECT b.series_id, b.feature_name, b.observation_date, b.as_of_date, b.feature_value,
               y.as_of_date AS yoy_as_of_date, y.feature_value AS yoy_value
        FROM bounded b
        LEFT JOIN current_features y ON b.feature_name = 'mom' AND y.feature_name = 'yoy'
          AND y.series_id = b.series_id AND y.observation_date = b.observation_date
        WHERE b.observation_date = latest_stored OR (
            b.observation_date <= latest AND (
                (b.frequency = 'daily' AND finite AND available_rank <= 4) OR
                (b.frequency = 'weekly' AND b.observation_date >= latest - INTERVAL '21 days') OR
                (b.frequency = 'monthly' AND b.observation_date >= latest - INTERVAL '3 months') OR
                (b.frequency = 'quarterly' AND b.observation_date >= latest - INTERVAL '9 months')
            )
        ) ORDER BY b.series_id, b.feature_name, b.observation_date;
    """
    params = [item for source in sources for item in source] + [METHODOLOGY_VERSION, today]
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    finally:
        connection.close()
    # Raw ICSA is an observation history, not a fabricated level feature. Its
    # computation date is not applicable; keep that metadata explicitly null.
    raw = load_series_history("ICSA", end_date=today)
    rows.extend(("ICSA", "raw", point["observation_date"], None, point["value"]) for point in raw["observations"])
    from app.local_ism import SERIES
    local_histories = {}
    for sid in SERIES:
        local_histories[sid] = load_series_history(sid, end_date=today)
        rows.extend((sid, "raw", p["observation_date"], None, p["value"]) for p in local_histories[sid]["observations"])
    result = compare_overview_readings(rows)
    for item in result:
        if item["series_id"] in local_histories:
            points = {str(p["observation_date"]): p for p in local_histories[item["series_id"]]["observations"]}
            for key in ("current", "previous", "three_periods_ago"):
                if item[key]:
                    item[key].update({k: v for k, v in points[item[key]["observation_date"]].items() if k not in ("value", "observation_date")})
            item["source_url"] = item["current"]["source_url"] if item["current"] else SERIES[item["series_id"]]["source_url"]
            item["attribution"] = SERIES[item["series_id"]]["attribution"]
    return result
