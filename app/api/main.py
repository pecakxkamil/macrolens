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
from app.analytics import series_catalog
from app.analytics import usa_economy_now


logger = logging.getLogger(__name__)

SNAPSHOT_UNAVAILABLE_DETAIL = "Current macro snapshot is temporarily unavailable."
HISTORY_UNAVAILABLE_DETAIL = "Historical chart data is temporarily unavailable."
CATALOG_UNAVAILABLE_DETAIL = "Indicator catalog is temporarily unavailable."
DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

app = FastAPI(title="MacroLens API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(DEVELOPMENT_CORS_ORIGINS),
    allow_methods=["GET"],
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/economy/us")
def get_us_economy_now() -> dict:
    return _current_snapshot(usa_economy_now.build_usa_economy_now)


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
