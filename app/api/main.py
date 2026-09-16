"""FastAPI application for MacroLens API v1."""

import logging
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder

from app.analytics import consumer_snapshot
from app.analytics import financial_conditions_snapshot
from app.analytics import growth_snapshot
from app.analytics import housing_snapshot
from app.analytics import inflation_snapshot
from app.analytics import labor_snapshot
from app.analytics import usa_economy_now


logger = logging.getLogger(__name__)

SNAPSHOT_UNAVAILABLE_DETAIL = "Current macro snapshot is temporarily unavailable."

app = FastAPI(title="MacroLens API", version="0.1.0")


def _current_snapshot(builder: Callable[[], dict]) -> dict:
    try:
        return jsonable_encoder(builder())
    except Exception as error:
        logger.exception("Current macro snapshot unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SNAPSHOT_UNAVAILABLE_DETAIL,
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
