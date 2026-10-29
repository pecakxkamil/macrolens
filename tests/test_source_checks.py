"""Availability-check regression tests: mocked providers and isolated persistence."""
import copy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app import source_checks as recording
from app.analytics import source_checks as coverage
from app.ingestion import ingest_series as ingest
from app.ingestion import sync_release_calendar as calendar
from app.ingestion import sync_fomc_calendar as fomc

TODAY = date(2026, 10, 23)
START = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)


@pytest.fixture
def records(monkeypatch):
    runs = {}
    monkeypatch.setattr(recording, 'write_run', lambda row: runs.__setitem__(row['id'], copy.deepcopy(row)))
    clock = iter(START + timedelta(minutes=n) for n in range(100))
    monkeypatch.setattr(recording, 'utc_now', lambda: next(clock))
    return runs


class Connection:
    def __init__(self):
        self.rows = {}
    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, params):
        if isinstance(params, dict):
            self.rows[(params['observation_date'], params['vintage_date'])] = params['value']
    def commit(self): pass
    def rollback(self): pass
    def close(self): pass


def setup_ingestion(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(ingest, '_load_configured_series_ids', lambda: {'UNRATE'})
    monkeypatch.setattr(ingest, 'get_connection', lambda: connection)
    monkeypatch.setattr(ingest, 'save_raw_response', lambda *args: Path('mock-raw.json'))
    monkeypatch.setattr(ingest, 'fetch_series_observations', lambda _: {'observations': [
        {'date': '2026-09-01', 'realtime_start': '2026-10-02', 'value': '4.2'}]})
    return connection


def summary(records):
    return coverage.summarize_checks(list(records.values()), TODAY)


def source(result, resource='fred:UNRATE'):
    return next(row for row in result['sources'] if row['resource'] == resource)


def test_success_with_new_data_and_without_new_data_both_advance_check(monkeypatch, records):
    connection = setup_ingestion(monkeypatch)
    ingest.ingest_series('UNRATE')
    first = source(summary(records))
    assert first['status'] == 'success'
    assert first['last_attempt_at'] == START.isoformat()
    assert first['last_success_at'] == (START + timedelta(minutes=1)).isoformat()
    assert len(connection.rows) == 1
    ingest.ingest_series('UNRATE')  # Identical response, zero new observations.
    second = source(summary(records))
    assert len(connection.rows) == 1
    assert second['last_success_at'] > first['last_success_at']
    assert second['provider'] == 'FRED'
    assert len(records) == 2


def test_failed_refresh_preserves_success_and_redacts_error(monkeypatch, records, capsys):
    setup_ingestion(monkeypatch)
    ingest.ingest_series('UNRATE')
    previous = source(summary(records))['last_success_at']
    def fail(_): raise RuntimeError('private-provider-key')
    monkeypatch.setattr(ingest, 'fetch_series_observations', fail)
    with pytest.raises(RuntimeError): ingest.ingest_series('UNRATE')
    result = summary(records)
    row = source(result)
    assert row['status'] == 'error' and row['last_success_at'] == previous
    assert row['last_attempt_at'] > previous
    assert row['error_code'] == 'refresh_failed'
    assert 'private-provider-key' not in str(result)
    assert result['status'] == 'partial'


def successful(resource, finished=START, scope=None):
    return dict(resource=resource, attempted_at=finished-timedelta(seconds=10), finished_at=finished,
                status='success', scope=scope or {}, error_code=None)


def full_rows():
    return [successful(resource, START + timedelta(minutes=i),
        {'start_date': str(TODAY), 'end_date': str(TODAY + timedelta(days=6)), 'series_ids': sorted(coverage.FRED_SERIES)}
        if resource == 'fred:calendar' else {'dates': ['2026-10-28']}
        if resource == 'fed:calendar' else {'confirmed_from':'2026-01-05','confirmed_through':'2026-12-03'}
        if resource == 'ism:calendar' else {'confirmed_years':[2026]}
        if resource == 'michigan:calendar' else {'confirmed_from':'2026-01-01','confirmed_through':'2026-12-31'}
        if resource == 'adp:calendar' else {'schedule_checked':True,'csv_validated':True,'confirmed_years':[2026]}
        if resource == 'nyfed:empire-state' else {'schedule_checked':True,'report_checked':True,'exhibit1_validated':True,'result_pending':False,'confirmed_years':[2026,2027]}
        if resource == 'census:ft900' else {'latest_publication_discovered': True}
        if resource.startswith('ism:') else {}) for i, resource in enumerate(coverage.REQUIRED)]


def test_partial_and_complete_coverage_use_oldest_success_not_one_series_latest():
    rows = full_rows()
    complete = coverage.summarize_checks(rows, TODAY)
    assert complete['status'] == 'complete' and complete['checked_at'] == START.isoformat()
    assert complete['checked_at'] != rows[-1]['finished_at'].isoformat()
    partial = coverage.summarize_checks(rows[:1], TODAY)
    assert partial['status'] == 'partial' and partial['checked_count'] == 1
    assert partial['required_count'] == len(coverage.REQUIRED)
    assert source(partial, 'ism:ISM_MANUFACTURING_PMI')['last_success_at'] is None


def test_calendar_scope_must_cover_all_overview_sources_and_current_window():
    rows = full_rows()
    calendar_row = next(row for row in rows if row['resource'] == 'fred:calendar')
    calendar_row['scope']['end_date'] = str(TODAY)
    outdated = source(coverage.summarize_checks(rows, TODAY), 'fred:calendar')
    assert outdated['last_success_at'] is not None
    assert outdated['coverage_checked_at'] is None
    calendar_row['scope']['end_date'] = str(TODAY + timedelta(days=6))
    calendar_row['scope']['series_ids'] = ['UNRATE']
    assert coverage.summarize_checks(rows, TODAY)['status'] == 'partial'


def test_absent_metadata_never_infers_check_from_page_or_observations():
    result = coverage.summarize_checks([], TODAY)
    assert result['status'] == 'not_recorded' and result['checked_at'] is None
    assert all(row['last_attempt_at'] is None and row['last_success_at'] is None for row in result['sources'])
    row = successful('fred:UNRATE', datetime(2026, 10, 23))  # No implicit timezone.
    assert coverage.summarize_checks([row], TODAY)['checked_at'] is None


def test_old_ism_document_import_does_not_record_a_latest_publication_check(monkeypatch, records, tmp_path):
    from app.ingestion import import_ism as ism
    from tests.test_ism import document
    report = ism.parse_report(document(), 'manufacturing')
    assert report['report_month'] == date(2024, 12, 1)
    connection = Connection()
    connection.fetchone = lambda: None  # An already imported historical document.
    monkeypatch.setattr(ism, 'get_connection', lambda: connection)
    monkeypatch.setattr(ism, 'RAW_ROOT', tmp_path / 'raw' / 'ism')
    assert ism.store_report(report, 'https://www.prnewswire.com/news-releases/old-release.html', document().encode()) is False
    assert not records
    assert summary(records)['checked_at'] is None
    # Even a generic document-fetch success must not qualify as latest discovery.
    assert coverage.summarize_checks([successful('ism:ISM_MANUFACTURING_PMI')], TODAY)['checked_at'] is None


def test_partial_fed_monthly_page_preserves_prior_complete_success(records, tmp_path):
    from tests.test_fomc_calendar import schedule_html, monthly_html
    def respond(request):
        return httpx.Response(200, text=schedule_html() if str(request.url) == fomc.SOURCE_URL else monthly_html())
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        fomc.sync_schedule(client, tmp_path/'derived/fed.json', tmp_path/'raw', START)
    previous = source(summary(records), 'fed:calendar')['last_success_at']
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=schedule_html())
        if str(request.url) == fomc.SOURCE_URL else httpx.Response(404))) as client:
        fomc.sync_schedule(client, tmp_path/'derived/fed.json', tmp_path/'raw', START)
    row = source(summary(records), 'fed:calendar')
    assert row['status'] == 'partial' and row['last_success_at'] == previous
    assert row['scope']['missing_times'] == ['2026-10-28']
    assert row['error_code'] == 'decision_times_unavailable'


def test_calendar_failure_before_storage_records_attempt_without_success(monkeypatch, records):
    monkeypatch.setattr(calendar, 'active_configured_series_ids', lambda: ['UNRATE'])
    def fail(_): raise RuntimeError('provider unavailable')
    monkeypatch.setattr(calendar, 'fetch_series_release', fail)
    with pytest.raises(RuntimeError): calendar.sync_release_calendar(TODAY, TODAY + timedelta(days=6))
    row = source(summary(records), 'fred:calendar')
    assert row['status'] == 'error' and row['last_success_at'] is None
    assert row['last_attempt_at'] == START.isoformat()


def test_metadata_write_failure_never_changes_success_into_fabricated_metadata(monkeypatch, caplog):
    def fail(_): raise RuntimeError('private-db-password')
    monkeypatch.setattr(recording, 'write_run', fail)
    with recording.availability_check('fred:UNRATE'):
        pass
    assert 'not recorded' in caplog.text
    assert 'private-db-password' not in caplog.text


def test_missing_schema_only_reuses_explicit_fed_date_fetch_not_all_sources(monkeypatch):
    def fail(): raise RuntimeError('missing table')
    monkeypatch.setattr(coverage, 'get_connection', fail)
    monkeypatch.setattr(coverage, 'read_schedule', lambda: {'retrieved_at': START.isoformat(),
        'events': [{'release_date': '2026-10-28'}]})
    result = coverage.load_source_checks(TODAY)
    assert result['status'] == 'partial' and result['checked_count'] == 1
    fed = source(result, 'fed:calendar')
    assert fed['scope']['legacy_dates_only'] is True and fed['status'] == 'partial'
    monkeypatch.setattr(coverage, 'read_schedule', lambda: {'retrieved_at': None, 'events': []})
    assert coverage.load_source_checks(TODAY)['checked_at'] is None


def test_recording_sql_uses_aware_timestamps_and_append_only_run_ids(monkeypatch):
    calls = []
    connection = Connection()
    connection.execute = lambda sql, params: calls.append((sql, params))
    monkeypatch.setattr(recording, 'get_connection', lambda: connection)
    run = dict(id='test-id', resource='fred:UNRATE', attempted_at=START,
               finished_at=START + timedelta(seconds=1), status='success', scope={}, error_code=None)
    recording.write_run(run)
    sql, params = calls[0]
    assert 'ON CONFLICT (id)' in sql and params[2].tzinfo is timezone.utc
    assert params[3].tzinfo is timezone.utc
    assert 'TIMESTAMPTZ' in Path('app/database/source_checks.sql').read_text()


def test_narrower_followup_keeps_last_success_and_previous_dashboard_coverage():
    broad = successful('fred:calendar', START, {
        'start_date': str(TODAY), 'end_date': str(TODAY + timedelta(days=6)),
        'series_ids': sorted(coverage.FRED_SERIES)})
    narrow = successful('fred:calendar', START + timedelta(hours=1), {
        'start_date': '2025-01-01', 'end_date': '2025-01-31', 'series_ids': ['UNRATE']})
    result = source(coverage.summarize_checks([broad, narrow], TODAY), 'fred:calendar')
    assert result['last_success_at'] == narrow['finished_at'].isoformat()
    assert result['coverage_checked_at'] == broad['finished_at'].isoformat()
    assert result['successful_scope'] == narrow['scope'] and result['coverage_scope'] == broad['scope']


def test_loading_is_one_read_only_query_and_never_advances_provenance(monkeypatch, records):
    connection = Connection()
    calls = []
    connection.execute = lambda sql, params: calls.append((sql, params))
    stored = successful('fred:UNRATE')
    connection.fetchall = lambda: [tuple(stored[key] for key in
        ('resource', 'attempted_at', 'finished_at', 'status', 'scope', 'error_code'))]
    monkeypatch.setattr(coverage, 'get_connection', lambda: connection)
    monkeypatch.setattr(coverage, 'read_schedule', lambda: {'retrieved_at': None, 'events': []})
    first = coverage.load_source_checks(TODAY)
    assert coverage.load_source_checks(TODAY) == first
    assert len(calls) == 2 and all('SELECT' in sql and 'INSERT' not in sql for sql, _ in calls)
    assert first['checked_at'] == START.isoformat() and not records
    assert first['metadata_status'] == 'available'

@pytest.mark.parametrize('http_status,fetch_status',[(200,'success'),(404,'error'),(500,'error')])
def test_fed_time_metadata_distinguishes_unconfirmed_time_from_fetch_error(records,tmp_path,http_status,fetch_status):
    from tests.test_fomc_calendar import schedule_html,monthly_html
    def respond(request):
        return httpx.Response(200,text=schedule_html()) if str(request.url)==fomc.SOURCE_URL else httpx.Response(http_status,text=monthly_html(clock='TBA'))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        payload=fomc.sync_schedule(client,tmp_path/'derived/fed.json',tmp_path/'raw',START)
    row=source(summary(records),'fed:calendar')
    assert row['scope']['time_checks'][0]['fetch_status']==fetch_status
    assert row['scope']['time_checks'][0]['time_status']=='unconfirmed'
    assert row['status']=='partial' and payload['events'][0]['release_time'] is None
    assert 'time_checks' not in payload  # Provenance only, no stored schedule/data change.
