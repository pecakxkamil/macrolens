import copy
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.analytics import economy_brief as brief, macro_state


@pytest.fixture
def snapshot():
    return json.loads((Path(__file__).parent / 'fixtures' / 'macro_state_snapshot.json').read_text(encoding='utf-8'))


def stub_sections(monkeypatch, snapshot):
    monkeypatch.setattr(brief, "load_fed_target", lambda today: {"availability": "unavailable"})
    monkeypatch.setattr(brief, "policy_outlook", lambda now: {"schedule_status": "not_synced", "next_decision": None})
    monkeypatch.setattr(brief.usa_economy_now, 'build_usa_economy_now', lambda: snapshot)
    monkeypatch.setattr(brief, 'load_reading_comparisons', lambda today: [])
    monkeypatch.setattr(brief.release_calendar, 'list_calendar_events', lambda start, end: {'start_date': start, 'end_date': end, 'events': []})


def test_reuses_identical_snapshot_and_existing_interpretations(monkeypatch, snapshot):
    stub_sections(monkeypatch, snapshot)
    calls = []
    monkeypatch.setattr(brief.usa_economy_now, 'build_usa_economy_now', lambda: calls.append('snapshot') or snapshot)
    original = copy.deepcopy(snapshot)
    result = brief.build_brief(datetime(2026, 10, 18, 12, tzinfo=timezone.utc))
    assert calls == ['snapshot']
    assert result['state']['data'] == macro_state.build_macro_state(snapshot)
    assert result['snapshot']['data'] is snapshot and snapshot == original
    assert result['history_type'] == 'current_vintage'


@pytest.mark.parametrize('frequency,observed,expected', [
    ('monthly', '2026-01-01', '2025-12-01'), ('quarterly', '2026-01-01', '2025-10-01'),
    ('weekly', '2026-01-03', '2025-12-27'), ('monthly', '2024-03-01', '2024-02-01')])
def test_previous_appropriate_calendar_period(frequency, observed, expected):
    assert str(brief.previous_period(date.fromisoformat(observed), frequency)) == expected


def test_comparisons_reuse_transforms_and_explicit_periods_and_units():
    rows = [('CPIAUCSL', 'yoy', date(2026, 8, 1), date(2026, 9, 10), Decimal('3.2')),
            ('CPIAUCSL', 'yoy', date(2026, 7, 1), date(2026, 9, 10), Decimal('3.0')),
            ('GDPC1', 'qoq_annualized', date(2026, 7, 1), date(2026, 10, 10), 2),
            ('GDPC1', 'qoq_annualized', date(2026, 4, 1), date(2026, 10, 10), 3)]
    result = brief.compare_readings(rows)
    cpi, gdp = result[1:3]
    assert cpi['change'] == pytest.approx(.2) and cpi['change_unit'] == 'percentage points'
    assert cpi['current']['observation_date'] == '2026-08-01'
    assert cpi['previous']['observation_date'] == '2026-07-01'
    assert cpi['current']['feature_as_of_date'] == '2026-09-10'
    assert gdp['change'] == -1 and gdp['previous']['observation_date'] == '2026-04-01'
    assert 'quarter' in gdp['change_type']
    assert 'release_date' not in cpi['current'] and 'vintage_date' not in cpi['current']


@pytest.mark.parametrize('missing', [None, float('nan'), float('inf')])
def test_missing_prior_period_never_bridges_or_becomes_zero(missing):
    result = brief.compare_readings([
        ('UNRATE', 'level', '2026-08-01', '2026-09-01', 4.1),
        ('UNRATE', 'level', '2026-07-01', '2026-09-01', missing),
        ('UNRATE', 'level', '2026-06-01', '2026-09-01', 3.8)])[0]
    assert result['current']['value'] == 4.1
    assert result['previous'] is None and result['change'] is None
    assert result['expected_previous_observation_date'] == '2026-07-01'


def test_latest_available_reading_exposes_newer_missing_period():
    item = brief.compare_readings([('UNRATE', 'level', '2026-08-01', '2026-09-01', None),
                                  ('UNRATE', 'level', '2026-07-01', '2026-09-01', 4.0)])[0]
    assert item['current']['observation_date'] == '2026-07-01'
    assert item['latest_stored_observation_date'] == '2026-08-01'
    assert item['change'] is None


def test_six_explicit_comparisons_missing_readings_are_explicit():
    items = brief.compare_readings([])
    assert [item['series_id'] for item in items] == ['UNRATE', 'CPIAUCSL', 'GDPC1', 'PCEC96', 'HOUST', 'NFCI']
    assert all(item['current'] is None and item['previous'] is None and item['change'] is None for item in items)


def test_bulk_query_uses_same_vintage_order_once(monkeypatch):
    calls = []
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params): calls.append((sql, params))
        def fetchall(self): return []
    class Connection:
        def cursor(self): return Cursor()
        def close(self): calls.append('closed')
    from app.analytics import overview_readings
    monkeypatch.setattr(overview_readings, 'get_connection', Connection)
    result = brief.load_comparisons(date(2026, 10, 18))
    sql, params = calls[0]
    assert len(calls) == 2 and len(result) == 6
    assert 'as_of_date DESC, computed_at DESC, id DESC' in sql
    assert params[-2:] == ['v1', date(2026, 10, 18)]


@pytest.mark.parametrize('failure', ['snapshot', 'state', 'changes', 'calendar'])
def test_partial_failures_are_sanitized_and_do_not_block_other_sections(monkeypatch, snapshot, failure):
    stub_sections(monkeypatch, snapshot)
    def fail(*args, **kwargs): raise RuntimeError('secret connection detail')
    if failure == 'snapshot': monkeypatch.setattr(brief.usa_economy_now, 'build_usa_economy_now', fail)
    if failure == 'state': monkeypatch.setattr(brief.macro_state, 'build_macro_state', fail)
    if failure == 'changes': monkeypatch.setattr(brief, 'load_reading_comparisons', fail)
    if failure == 'calendar': monkeypatch.setattr(brief.release_calendar, 'list_calendar_events', fail)
    result = TestClient(app).get('/api/v1/economy/us/brief')
    assert result.status_code == 200
    body = result.json()
    assert body[failure]['status'] == 'unavailable' and body[failure]['data'] is None
    assert 'secret' not in result.text
    if failure != 'changes': assert body['changes']['status'] == 'ready'
    if failure != 'calendar': assert body['calendar']['status'] == 'ready'


def test_calendar_empty_is_ready_and_warsaw_midnight_defines_seven_day_window(monkeypatch, snapshot):
    stub_sections(monkeypatch, snapshot)
    result = brief.build_brief(datetime(2026, 10, 17, 22, 30, tzinfo=timezone.utc))
    assert result['calendar_start_date'] == '2026-10-18'
    assert result['calendar_end_date'] == '2026-10-24'
    assert result['calendar']['status'] == 'ready' and result['calendar']['data']['events'] == []
    assert result['timezone'] == 'Europe/Warsaw'


def test_api_serializes_dates_and_decimal_without_changing_existing_endpoint(monkeypatch, snapshot):
    stub_sections(monkeypatch, snapshot)
    snapshot['labor']['unemployment']['level'] = Decimal('4.1')
    body = TestClient(app).get('/api/v1/economy/us/brief').json()
    assert body['snapshot']['data']['labor']['unemployment']['level'] == 4.1
    assert body['state']['data']['domains']['labor']['readings'][1]['value'] == 4.1
    assert 'assembled_at' in body and 'mci' not in body


def test_classification_basis_preserves_inputs_labels_and_dates(snapshot):
    original = copy.deepcopy(snapshot)
    result = brief.classification_basis(snapshot)
    assert snapshot == original
    for domain, items in result.items():
        for item in items:
            component = snapshot[domain] if item['component'] == 'overall' else snapshot[domain][item['component']]
            assert item['classification'] == component[item['field']]
            assert item['rule'] and item['short']
            if item['component'] != 'overall':
                assert item['observation_date'] == component['observation_date']
                assert item['feature_as_of_date'] == component['feature_as_of_date']
            for input_value in item['inputs']:
                assert input_value['value'] == component[input_value['feature_name']]
    assert {item['component'] for item in result['labor']} >= {'overall', 'payrolls', 'unemployment', 'initial_claims', 'continuing_claims'}
    assert {item['field'] for item in result['financial_conditions'] if item['component'] == 'nfci'} == {'position', 'direction'}


def test_cpi_decelerating_is_three_month_annualized_versus_yoy_not_successive_yoy(snapshot):
    from app.analytics.inflation_snapshot import classify_inflation_momentum
    component = snapshot['inflation']['headline_cpi']
    component.update(annualized_3m=2.5, yoy=3.71, momentum=classify_inflation_momentum(2.5, 3.71))
    item = next(item for item in brief.classification_basis(snapshot)['inflation'] if item['component'] == 'headline_cpi')
    assert item['classification'] == 'decelerating'
    assert [value['feature_name'] for value in item['inputs']] == ['annualized_3m', 'yoy']
    assert [value['value'] for value in item['inputs']] == [2.5, 3.71]
    change = brief.compare_readings([('CPIAUCSL', 'yoy', '2026-08-01', '2026-09-11', 3.71), ('CPIAUCSL', 'yoy', '2026-07-01', '2026-09-11', 3.54)])[1]
    assert change['change'] == pytest.approx(.17)
    assert 'does not compare successive YoY' in item['rule']


def test_gdp_accelerating_is_current_quarter_versus_yoy_not_previous_quarter_rate(snapshot):
    from app.analytics.growth_snapshot import classify_growth_momentum
    component = snapshot['growth']['real_gdp']
    component.update(qoq_annualized=2.22, yoy=1.6, momentum=classify_growth_momentum(2.22, 1.6))
    item = next(item for item in brief.classification_basis(snapshot)['growth'] if item['component'] == 'real_gdp')
    assert item['classification'] == 'accelerating'
    assert [value['feature_name'] for value in item['inputs']] == ['qoq_annualized', 'yoy']
    assert [value['value'] for value in item['inputs']] == [2.22, 1.6]
    change = brief.compare_readings([('GDPC1', 'qoq_annualized', '2026-04-01', '2026-09-30', 2.22), ('GDPC1', 'qoq_annualized', '2026-01-01', '2026-09-30', 2.49)])[2]
    assert change['change'] == pytest.approx(-.27)
    assert 'does not compare successive quarterly' in item['rule']


def test_basis_covers_every_exposed_classification_and_cross_current(snapshot):
    state = macro_state.build_macro_state(snapshot)
    basis = brief.classification_basis(snapshot)
    for domain, source in state['domains'].items():
        for key, classification in source['classifications'].items():
            # Only selected readings/evidence are presented in Economy Brief.
            if key.split('.')[0] in {'job_openings', 'labor_force_participation', 'durable_goods_orders'}: continue
            component, field = key.split('.') if '.' in key else ('overall', key)
            assert any(item['component'] == component and item['field'] == field and item['classification'] == classification for item in basis[domain])
