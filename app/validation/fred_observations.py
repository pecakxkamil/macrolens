"""Validation for FRED observations payloads."""

from datetime import date
from decimal import Decimal, InvalidOperation
import re


ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_OBSERVATION_FIELDS = ("date", "realtime_start", "value")


class FredObservationValidationError(Exception):
    """Raised when a FRED observations payload is invalid."""


def _validate_iso_date(value: object, field_name: str, index: int) -> None:
    if not isinstance(value, str) or not ISO_DATE_PATTERN.fullmatch(value):
        raise FredObservationValidationError(
            f"Observation {index} has invalid {field_name}: {value!r}"
        )

    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise FredObservationValidationError(
            f"Observation {index} has invalid {field_name}: {value!r}"
        ) from error


def _is_numeric_value(value: object) -> bool:
    try:
        numeric_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return numeric_value.is_finite()


def validate_fred_observations(payload: object) -> dict:
    """Validate a FRED observations payload and return a small summary."""
    if not isinstance(payload, dict):
        raise FredObservationValidationError("FRED payload must be a dictionary.")

    if "observations" not in payload:
        raise FredObservationValidationError(
            'FRED payload is missing "observations".'
        )

    observations = payload["observations"]
    if not isinstance(observations, list) or not observations:
        raise FredObservationValidationError(
            "FRED observations must be a non-empty list."
        )

    seen_dates = set()
    numeric_observations = 0
    missing_observations = 0

    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise FredObservationValidationError(
                f"Observation {index} must be a dictionary."
            )

        missing_fields = [
            field
            for field in REQUIRED_OBSERVATION_FIELDS
            if field not in observation
        ]
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise FredObservationValidationError(
                f"Observation {index} is missing required fields: {fields}"
            )

        observation_date = observation["date"]
        vintage_date = observation["realtime_start"]
        _validate_iso_date(observation_date, "date", index)
        _validate_iso_date(vintage_date, "realtime_start", index)

        date_pair = (observation_date, vintage_date)
        if date_pair in seen_dates:
            raise FredObservationValidationError(
                "Duplicate observation date/vintage pair: "
                f"{observation_date}, {vintage_date}"
            )
        seen_dates.add(date_pair)

        value = observation["value"]
        if value == ".":
            missing_observations += 1
        elif _is_numeric_value(value):
            numeric_observations += 1
        else:
            raise FredObservationValidationError(
                f"Observation {index} has invalid numeric value: {value!r}"
            )

    if numeric_observations == 0:
        raise FredObservationValidationError(
            "FRED observations must include at least one numeric value."
        )

    return {
        "total_observations": len(observations),
        "numeric_observations": numeric_observations,
        "missing_observations": missing_observations,
    }
