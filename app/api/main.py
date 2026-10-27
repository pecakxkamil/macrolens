"""FastAPI application for MacroLens API v1."""

import logging
from collections.abc import Callable
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from app.analytics import consumer_snapshot
from app.analytics import financial_conditions_snapshot
from app.analytics import growth_snapshot
from app.analytics import history
from app.analytics import housing_snapshot
from app.analytics import inflation_snapshot
from app.analytics import labor_snapshot
from app.analytics import market_comparison
from app.analytics import macro_conditions_index
from app.analytics import point_in_time_mci
from app.analytics import macro_state
from app.analytics import release_calendar
from app.analytics import relationships
from app.analytics import series_catalog
from app.analytics import usa_economy_now


logger = logging.getLogger(__name__)

SNAPSHOT_UNAVAILABLE_DETAIL = "Current macro snapshot is temporarily unavailable."
HISTORY_UNAVAILABLE_DETAIL = "Historical chart data is temporarily unavailable."
CATALOG_UNAVAILABLE_DETAIL = "Indicator catalog is temporarily unavailable."
CALENDAR_UNAVAILABLE_DETAIL = "Macro calendar is temporarily unavailable."
MCI_UNAVAILABLE_DETAIL = "Macro Conditions Index is temporarily unavailable."
RELATIONSHIPS_UNAVAILABLE_DETAIL = "Macro relationships are temporarily unavailable."
DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

app = FastAPI(title="MacroLens API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(DEVELOPMENT_CORS_ORIGINS),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _current_snapshot(builder: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(builder())
    except Exception as error:
        logger.exception("Current macro snapshot unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SNAPSHOT_UNAVAILABLE_DETAIL,
        ) from error


def _history_response(loader: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(loader())
    except (history.UnknownSeriesError, history.UnsupportedFeatureError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except history.InvalidDateRangeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception as error:
        logger.exception("Historical chart data unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=HISTORY_UNAVAILABLE_DETAIL,
        ) from error


def _catalog_response(loader: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(loader())
    except series_catalog.UnknownCatalogSeriesError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except Exception as error:
        logger.exception("Indicator catalog unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=CATALOG_UNAVAILABLE_DETAIL,
        ) from error


def _calendar_response(loader: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(loader())
    except release_calendar.UnknownReleaseError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (release_calendar.InvalidCalendarRangeError, release_calendar.InvalidCalendarCategoryError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception as error:
        logger.exception("Macro calendar unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=CALENDAR_UNAVAILABLE_DETAIL,
        ) from error


def _relationships_response(loader: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(loader())
    except (history.UnknownSeriesError, history.UnsupportedFeatureError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (history.InvalidDateRangeError, relationships.InvalidRelationshipSelectionError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception as error:
        logger.exception("Macro relationships unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=RELATIONSHIPS_UNAVAILABLE_DETAIL,
        ) from error


def _mci_response(loader: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(loader())
    except history.InvalidDateRangeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception as error:
        logger.exception("Macro Conditions Index unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MCI_UNAVAILABLE_DETAIL,
        ) from error


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/economy/us")
def get_us_economy_now() -> dict:
    return _current_snapshot(usa_economy_now.build_usa_economy_now)


@app.get("/api/v1/economy/us/mci")
def get_macro_conditions_index() -> dict:
    return _mci_response(macro_conditions_index.get_current_index)


@app.get("/api/v1/economy/us/mci/history")
def get_macro_conditions_index_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    return _mci_response(lambda: macro_conditions_index.get_index_history(start_date, end_date))


@app.get("/api/v1/economy/us/mci/point-in-time")
def get_pit_mci() -> dict:
    return _mci_response(point_in_time_mci.get_current)


@app.get("/api/v1/economy/us/mci/point-in-time/history")
def get_pit_mci_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    return _mci_response(lambda: point_in_time_mci.get_history(start_date, end_date))


@app.get("/api/v1/economy/us/mci/point-in-time/{as_of_date}")
def get_pit_mci_audit(as_of_date: date) -> dict:
    return _mci_response(lambda: point_in_time_mci.get_audit(as_of_date))


@app.get("/api/v1/economy/us/state")
def get_macro_state() -> dict:
    return _current_snapshot(macro_state.build_macro_state)


@app.get("/api/v1/economy/us/labor")
def get_labor() -> dict:
    return _current_snapshot(labor_snapshot.get_labor_snapshot)


@app.get("/api/v1/economy/us/inflation")
def get_inflation() -> dict:
    return _current_snapshot(inflation_snapshot.get_inflation_snapshot)


@app.get("/api/v1/economy/us/growth")
def get_growth() -> dict:
    return _current_snapshot(growth_snapshot.get_growth_snapshot)


@app.get("/api/v1/economy/us/consumer")
def get_consumer() -> dict:
    return _current_snapshot(consumer_snapshot.get_consumer_snapshot)


@app.get("/api/v1/economy/us/housing")
def get_housing() -> dict:
    return _current_snapshot(housing_snapshot.get_housing_snapshot)


@app.get("/api/v1/economy/us/financial-conditions")
def get_financial_conditions() -> dict:
    return _current_snapshot(
        financial_conditions_snapshot.get_financial_conditions_snapshot
    )


@app.get("/api/v1/series/{series_id}/history")
def get_series_history(
    series_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    return _history_response(
        lambda: history.load_series_history(series_id, start_date, end_date)
    )


@app.get("/api/v1/series")
def get_series_catalog() -> dict:
    return _catalog_response(series_catalog.list_active_series)


@app.get("/api/v1/series/{series_id}")
def get_series_metadata(series_id: str) -> dict:
    return _catalog_response(lambda: series_catalog.get_active_series(series_id))


@app.get("/api/v1/series/{series_id}/features")
def get_series_features(series_id: str) -> dict:
    return _catalog_response(lambda: series_catalog.list_available_features(series_id))


@app.get("/api/v1/analytics/yield-curve/2s10s/history")
def get_yield_curve_2s10s_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    return _history_response(
        lambda: history.load_yield_curve_2s10s_history(start_date, end_date)
    )


@app.get("/api/v1/series/{series_id}/features/{feature_name}/history")
def get_feature_history(
    series_id: str,
    feature_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    return _history_response(
        lambda: history.load_feature_history(
            series_id,
            feature_name,
            start_date,
            end_date,
        )
    )


@app.get("/api/v1/calendar")
def get_calendar(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    include_readings: bool = False,
) -> dict:
    if include_readings:
        from app.analytics.calendar_agenda import calendar_agenda
        return _calendar_response(lambda: calendar_agenda(start_date,end_date,category=category))
    return _calendar_response(
        lambda: release_calendar.list_calendar_events(start_date, end_date, category)
    )


@app.get("/api/v1/relationships/sources")
def get_relationship_sources() -> dict:
    from app.analytics.relationship_sources import list_sources
    return _relationships_response(list_sources)


@app.get("/api/v1/relationships/compare")
def get_relationship_comparison(
    left_series: str,
    right_series: str,
    left_feature: Optional[str] = None,
    right_feature: Optional[str] = None,
    third_series: Optional[str] = None,
    third_feature: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    return _relationships_response(lambda: relationships.compare_histories(
        left_series, right_series, left_feature, right_feature,
        third_series, third_feature, start_date, end_date,
    ))


@app.get("/api/v1/releases/{release_id}")
def get_release(release_id: int) -> dict:
    return _calendar_response(lambda: release_calendar.get_release_detail(release_id))


@app.get("/api/v1/market-comparison")
def get_market_comparison(assets: str = "NASDAQCOM", start_date: Optional[date] = None,
                          end_date: Optional[date] = None, macro_history_type: str = "point_in_time",
                          mode: str = "indexed") -> dict:
    try:
        return jsonable_encoder(market_comparison.compare_market(assets, start_date, end_date, macro_history_type, mode))
    except (history.InvalidDateRangeError, market_comparison.InvalidMarketComparisonError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        logger.exception("Market comparison unavailable")
        raise HTTPException(status_code=503, detail="Market comparison is temporarily unavailable.") from None


@app.get("/api/v1/market-comparison/lead-lag")
def get_macro_market_lead_lag(assets: str = "NASDAQCOM,CBBTCUSD", start_date: Optional[date] = None,
                             end_date: Optional[date] = None, macro_history_type: str = "point_in_time",
                             rolling_window: int = 24) -> dict:
    from app.analytics import macro_market_lead_lag
    try:
        return jsonable_encoder(macro_market_lead_lag.analyze(assets, start_date, end_date, macro_history_type, rolling_window))
    except (history.InvalidDateRangeError, market_comparison.InvalidMarketComparisonError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        logger.exception("Lead/lag analysis unavailable")
        raise HTTPException(status_code=503, detail="Lead/lag analysis is temporarily unavailable.") from None


@app.get("/api/v1/economy/us/brief")
def get_economy_brief() -> dict:
    from app.analytics.overview_refresh import read_brief
    return jsonable_encoder(read_brief())


@app.post("/api/v1/economy/us/brief/refresh")
def request_overview_refresh(calendar_start_date: Optional[date] = None, calendar_end_date: Optional[date] = None) -> dict:
    from app.analytics.overview_refresh import coordinator
    try:
        return coordinator.request(calendar_start_date,calendar_end_date) if calendar_start_date or calendar_end_date else coordinator.request()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except Exception:
        raise HTTPException(status_code=503, detail="Availability check unavailable; stored data remain accessible.") from None


@app.get("/api/v1/economy/us/brief/refresh")
def overview_refresh_status() -> dict:
    from app.analytics.overview_refresh import coordinator
    try:
        return coordinator.status()
    except Exception:
        raise HTTPException(status_code=503, detail="Availability check status unavailable.") from None


@app.get("/api/v1/economy/us/brief/history")
def overview_publication_history(revision: str, key: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    from uuid import UUID
    from app.analytics.overview_refresh import read_chart
    try:
        UUID(revision)
        return jsonable_encoder(read_chart(revision, key, start_date, end_date))
    except KeyError:
        raise HTTPException(status_code=409, detail="Overview snapshot expired or chart unavailable; reload Overview.") from None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Overview chart request.") from None
