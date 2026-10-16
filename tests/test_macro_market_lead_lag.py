from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.analytics import macro_market_lead_lag as lab, market_comparison as market
from app.analytics import macro_conditions_index as mci
from app.market_assets import load_market_assets


def fixtures(n=60, first=date(2019, 1, 1)):
    months = [mci._shift_month(first, i) for i in range(n)]
    macro = [{"as_of_date": str(mci._month_end(day)), "mci": 30 + (i*i % 23)} for i, day in enumerate(months)]
    prices = [{"observation_date": str(mci._month_end(day)), "value": 100 + i*i} for i, day in enumerate(months)]
    return macro, {"NASDAQCOM": prices}


def build(rows, prices, **kwargs):
    return lab.build_analysis(rows, prices, load_market_assets(), **kwargs)


def lag(result, k):
    return next(item for item in result['assets'][0]['lags'] if item['lag'] == k)


def test_sign_convention_calendar_pairs_and_deterministic_order():
    rows, prices = fixtures()
    result = build(rows, prices, start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
    assert result['macro_history_type'] == 'point_in_time'
    assert 'positive k means MCI change precedes' in result['lag_convention']
    assert [x['lag'] for x in result['assets'][0]['lags']] == list(range(-6, 7))
    for k in [-6, -3, 0, 3, 6]:
        pairs = lag(result, k)['pairs']
        assert len(pairs) == 12
        assert [p['anchor_date'] for p in pairs] == sorted(p['anchor_date'] for p in pairs)
        for pair in pairs:
            anchor = date.fromisoformat(pair['anchor_date'])
            assert pair['return_date'] == str(mci._month_end(mci._shift_month(mci._month(anchor), k)))
            if k < 0:
                assert pair['return_date'] < pair['anchor_date']
                assert pair['price_observation_date'] < pair['anchor_date']
    assert lag(result, 6)['pairs'][-1]['return_date'] == '2021-06-30'
    assert lag(result, -6)['pairs'][0]['return_date'] == '2019-07-31'


def test_missing_calendar_month_is_not_row_shifted_and_invalidates_delta():
    rows, prices = fixtures(10)
    rows.pop(3) # April is absent, not just null.
    result = build(rows, prices)
    pairs = lag(result, 1)['pairs']
    assert not any(p['anchor_date'] in ['2019-04-30', '2019-05-31'] for p in pairs)
    assert next(p for p in pairs if p['anchor_date'] == '2019-03-31')['return_date'] == '2019-04-30'
    assert '2019-04-30' in result['coverage']['missing_mci_change_dates']


def test_2025_pit_gaps_and_immediate_previous_null():
    rows, prices = fixtures(14, date(2025, 1, 1))
    for row in rows:
        if '2025-10' <= row['as_of_date'][:7] <= '2025-12': row['mci'] = None
    result = build(rows, prices)
    excluded = {'2025-10-31', '2025-11-30', '2025-12-31', '2026-01-31'}
    assert excluded <= set(result['coverage']['missing_mci_change_dates'])
    assert not any(p['anchor_date'] in excluded for p in lag(result, 0)['pairs'])


def test_stale_or_missing_prior_price_does_not_bridge_months():
    rows, prices = fixtures(10)
    prices['NASDAQCOM'].pop(3)
    result = build(rows, prices)
    dates = {p['return_date'] for p in lag(result, 0)['pairs']}
    assert '2019-04-30' not in dates and '2019-05-31' not in dates
    assert result['maximum_price_age_days'] == 7
    assert '2019-04-30' in result['assets'][0]['missing_price_dates']


@pytest.mark.parametrize('age,valid', [(0, True), (7, True), (8, False)])
def test_price_freshness_limit(age, valid):
    from datetime import timedelta
    rows, prices = fixtures(3)
    prices['NASDAQCOM'][-1]['observation_date'] = str(date(2019, 3, 31) - timedelta(days=age))
    result = build(rows, prices)
    assert any(p['anchor_date'] == '2019-03-31' for p in lag(result, 0)['pairs']) == valid


@pytest.mark.parametrize('window', [24, 36])
def test_rolling_true_calendar_window_and_range_boundary(window):
    rows, prices = fixtures()
    result = build(rows, prices, start_date=date(2022, 1, 1), rolling_window=window)
    point = lag(result, 3)['rolling'][0]
    assert point['valid_pairs'] == window and point['correlation'] is not None
    assert point['anchor_date'] == '2022-01-31'
    rows[25]['mci'] = None
    missing = build(rows, prices, start_date=date(2022, 1, 1), rolling_window=window)
    point = lag(missing, 3)['rolling'][0]
    assert point['correlation'] is None and point['valid_pairs'] == window - 2


@pytest.mark.parametrize('constant', [False, True])
def test_small_sample_or_zero_variance_is_null(constant):
    rows, prices = fixtures(8 if constant else 3)
    if constant:
        for row in rows: row['mci'] = 50
    result = build(rows, prices)
    assert lag(result, 0)['correlation'] is None


def test_no_future_dataset_fabrication():
    rows, prices = fixtures(10)
    result = build(rows, prices, available_through=date(2019, 10, 15))
    assert all(p['return_date'] <= '2019-09-30' for item in result['assets'][0]['lags'] for p in item['pairs'])


@pytest.mark.parametrize('query', ['assets=GOLD', 'assets=NASDAQCOM,NASDAQCOM', 'rolling_window=12',
    'macro_history_type=forecast', 'start_date=2025-12-01&end_date=2025-01-01'])
def test_api_validation(query):
    assert TestClient(app).get('/api/v1/market-comparison/lead-lag?' + query).status_code == 400


def test_api_bad_date_and_window_types():
    client = TestClient(app)
    assert client.get('/api/v1/market-comparison/lead-lag?end_date=bad').status_code == 422
    assert client.get('/api/v1/market-comparison/lead-lag?rolling_window=bad').status_code == 422


def test_loader_boundaries_pit_default_and_existing_comparison_unchanged(monkeypatch):
    rows, prices = fixtures()
    calls = []
    monkeypatch.setattr(lab.pit, 'get_history', lambda **kw: calls.append(('macro', kw)) or {'observations': rows})
    monkeypatch.setattr(market, 'load_market_history', lambda asset, cutoff: calls.append((asset, cutoff)) or prices['NASDAQCOM'])
    result = lab.analyze('NASDAQCOM', date(2020, 1, 1), date(2020, 12, 31))
    assert calls == [('macro', {'end_date': date(2020, 12, 31)}), ('NASDAQCOM', date(2021, 6, 30))]
    assert lag(result, 6)['n'] == 12
    assert result['data_loading_window']['start_date'] is None
    client = TestClient(app)
    assert client.get('/api/v1/market-comparison/lead-lag?assets=NASDAQCOM&start_date=2020-01-01&end_date=2020-12-31').json()['macro_history_type'] == 'point_in_time'
    before = market.build_comparison(rows, prices, load_market_assets())
    lab.build_analysis(rows, prices, load_market_assets())
    assert before == market.build_comparison(rows, prices, load_market_assets())
