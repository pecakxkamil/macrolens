from app.analytics.labor_state import (
    build_labor_momentum_state,
    classify_claims_momentum,
    classify_overall_labor_momentum,
    classify_payroll_momentum,
    classify_unemployment_momentum,
)


def test_payroll_momentum_improving():
    assert classify_payroll_momentum(250, 200) == "improving"


def test_payroll_momentum_weakening():
    assert classify_payroll_momentum(150, 200) == "weakening"


def test_payroll_momentum_stable():
    assert classify_payroll_momentum(200, 200) == "stable"


def test_unemployment_momentum_improving():
    assert classify_unemployment_momentum(-0.2) == "improving"


def test_unemployment_momentum_weakening():
    assert classify_unemployment_momentum(0.2) == "weakening"


def test_unemployment_momentum_stable():
    assert classify_unemployment_momentum(0) == "stable"


def test_claims_momentum_improving():
    assert classify_claims_momentum(210000, 225000) == "improving"


def test_claims_momentum_weakening():
    assert classify_claims_momentum(240000, 225000) == "weakening"


def test_claims_momentum_stable():
    assert classify_claims_momentum(225000, 225000) == "stable"


def test_overall_momentum_improving():
    assert (
        classify_overall_labor_momentum(["improving", "improving", "weakening"])
        == "improving"
    )


def test_overall_momentum_weakening():
    assert (
        classify_overall_labor_momentum(["weakening", "weakening", "improving"])
        == "weakening"
    )


def test_overall_momentum_mixed():
    assert classify_overall_labor_momentum(["improving", "weakening", "stable"]) == (
        "mixed"
    )


def test_build_labor_momentum_state_returns_structured_result():
    state = build_labor_momentum_state(
        "2026-09-04",
        {
            "monthly_change": 180,
            "monthly_change_ma_3m": 220,
            "monthly_change_ma_6m": 200,
        },
        {"level": 4.1, "change_3m": 0.1},
        {"moving_average_4w": 220000, "moving_average_13w": 220000},
    )

    assert state == {
        "as_of_date": "2026-09-04",
        "payrolls": {
            "monthly_change": 180,
            "monthly_change_ma_3m": 220,
            "monthly_change_ma_6m": 200,
            "momentum": "improving",
        },
        "unemployment": {
            "level": 4.1,
            "change_3m": 0.1,
            "momentum": "weakening",
        },
        "claims": {
            "moving_average_4w": 220000,
            "moving_average_13w": 220000,
            "momentum": "stable",
        },
        "overall_momentum": "mixed",
    }
