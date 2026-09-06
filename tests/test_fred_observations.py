import copy

import pytest

from app.validation.fred_observations import (
    FredObservationValidationError,
    validate_fred_observations,
)


def valid_payload():
    return {
        "observations": [
            {
                "date": "2024-01-01",
                "realtime_start": "2024-02-02",
                "value": "3.7",
            },
            {
                "date": "2024-02-01",
                "realtime_start": "2024-03-08",
                "value": ".",
            },
        ]
    }


def test_valid_payload_returns_summary_without_modifying_payload():
    payload = valid_payload()
    original_payload = copy.deepcopy(payload)

    summary = validate_fred_observations(payload)

    assert summary == {
        "total_observations": 2,
        "numeric_observations": 1,
        "missing_observations": 1,
    }
    assert payload == original_payload


def test_missing_observations_raises_validation_error():
    with pytest.raises(FredObservationValidationError):
        validate_fred_observations({})


def test_empty_observations_list_raises_validation_error():
    with pytest.raises(FredObservationValidationError):
        validate_fred_observations({"observations": []})


def test_invalid_date_raises_validation_error():
    payload = valid_payload()
    payload["observations"][0]["date"] = "2024-02-31"

    with pytest.raises(FredObservationValidationError):
        validate_fred_observations(payload)


def test_invalid_numeric_value_raises_validation_error():
    payload = valid_payload()
    payload["observations"][0]["value"] = "not-a-number"

    with pytest.raises(FredObservationValidationError):
        validate_fred_observations(payload)


def test_missing_value_marker_is_accepted():
    payload = valid_payload()
    payload["observations"].append(
        {
            "date": "2024-03-01",
            "realtime_start": "2024-04-05",
            "value": ".",
        }
    )

    summary = validate_fred_observations(payload)

    assert summary["missing_observations"] == 2
    assert summary["numeric_observations"] == 1


def test_duplicate_date_and_realtime_start_raises_validation_error():
    payload = valid_payload()
    payload["observations"].append(
        {
            "date": "2024-01-01",
            "realtime_start": "2024-02-02",
            "value": "3.8",
        }
    )

    with pytest.raises(FredObservationValidationError):
        validate_fred_observations(payload)


def test_payload_containing_only_missing_values_raises_validation_error():
    payload = {
        "observations": [
            {
                "date": "2024-01-01",
                "realtime_start": "2024-02-02",
                "value": ".",
            }
        ]
    }

    with pytest.raises(FredObservationValidationError):
        validate_fred_observations(payload)
