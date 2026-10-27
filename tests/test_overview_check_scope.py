"""Scope-only status projection; no database writes or provider requests."""
import copy
from datetime import date
import pytest
from app.analytics.overview_check_scope import scope_overview_checks
from app.analytics import source_checks, overview_refresh
from tests.test_source_checks import full_rows, TODAY


def brief(next_date='2026-10-28',missing=('2027-01-27',),status='partial',error='decision_times_unavailable'):
    rows=full_rows()
    fed=next(row for row in rows if row['resource']=='fed:calendar')
    fed.update(status=status,error_code=error)
    fed['scope'].update(dates=sorted(set([next_date,*missing])),missing_times=list(missing))
    checks=source_checks.summarize_checks(rows,TODAY)
    next_event={'event_type':'fomc_decision','release_date':next_date,
                'release_datetime_utc':None if next_date in missing else next_date+'T18:00:00+00:00'}
    return {'source_checks':checks,'calendar_start_date':str(TODAY),'calendar_end_date':'2026-10-29',
            'calendar':{'status':'ready','data':{'events':[next_event] if next_date<='2026-10-29' else []}},
            'policy':{'status':'ready','data':{'schedule_status':'available','next_decision':next_event}},
            'refresh':{'status':'partial','results':[{'resource':'fed:calendar','status':'partial','missing_times':list(missing)}]}}


def fed(result):return next(row for row in result['source_checks']['sources'] if row['resource']=='fed:calendar')


def test_distant_unconfirmed_time_does_not_lower_overview_and_keeps_full_result():
    original=brief();unchanged=copy.deepcopy(original)
    result=scope_overview_checks(original);checks=result['source_checks']
    assert checks['status']=='complete' and checks['full_scope_status']=='partial'
    assert fed(result)['status']=='partial' and fed(result)['overview_status']=='success'
    assert checks['fomc_schedule']['future_missing_times']==['2027-01-27']
    assert checks['fomc_schedule']['completeness_status']=='partial'
    assert result['refresh']==original['refresh'] and original==unchanged
    assert scope_overview_checks(result)==result


@pytest.mark.parametrize('next_date',['2026-10-28','2027-01-27'])
def test_missing_time_for_next_decision_stays_partial_even_outside_week(next_date):
    result=scope_overview_checks(brief(next_date,missing=(next_date,'2027-03-17')))
    assert result['source_checks']['status']=='partial'
    assert fed(result)['overview_status']=='partial'
    assert result['source_checks']['fomc_schedule']['displayed_missing_times']==[next_date]
    assert fed(result)['overview_error_code']=='displayed_decision_time_unavailable'


def test_another_fomc_event_in_displayed_window_is_also_required():
    data=brief()
    fed(data)['scope']['missing_times'].append('2026-10-29')
    fed(data)['scope']['dates'].append('2026-10-29')
    result=scope_overview_checks(data)
    assert result['source_checks']['status']=='partial'
    assert result['source_checks']['fomc_schedule']['displayed_missing_times']==['2026-10-29']


@pytest.mark.parametrize('resource',['fed:calendar','fred:ICSA'])
def test_download_or_parsing_failure_is_not_promoted_to_success(resource):
    data=brief();row=next(row for row in data['source_checks']['sources'] if row['resource']==resource)
    row.update(status='error',error_code='refresh_failed')
    result=scope_overview_checks(data)
    assert result['source_checks']['status']=='partial'
    assert next(row for row in result['source_checks']['sources'] if row['resource']==resource)['overview_status']=='error'


def test_successful_fetch_without_time_differs_from_failed_monthly_page():
    data=brief(missing=('2026-10-28','2027-01-27'))
    fed(data)['scope']['time_checks']=[{'release_date':'2026-10-28','fetch_status':'success','http_status':None,'time_status':'unconfirmed'}]
    result=scope_overview_checks(data)
    assert fed(result)['overview_status']=='partial'
    assert result['source_checks']['fomc_schedule']['source_check_status']=='success'
    fed(data)['scope']['time_checks'][0].update(fetch_status='error',http_status=500)
    result=scope_overview_checks(data)
    assert fed(result)['overview_status']=='error'
    assert result['source_checks']['fomc_schedule']['source_check_status']=='error'


@pytest.mark.parametrize('problem',['policy','calendar','legacy','unrelated_partial'])
def test_missing_scope_evidence_cannot_be_declared_complete(problem):
    data=brief()
    if problem in ('policy','calendar'):data[problem]['status']='unavailable'
    elif problem=='legacy':fed(data)['scope']['legacy_dates_only']=True
    else:fed(data)['error_code']='unknown_partial_scope'
    assert scope_overview_checks(data)['source_checks']['status']=='partial'


def test_cached_api_metadata_is_projected_without_rebuilding_data(monkeypatch):
    data=brief();data.update(data_revision='saved',reading_comparisons={'data':[{'value':194000}]})
    saved=copy.deepcopy(data)
    class Store:
        def publication(self):return ('saved',data)
    class Coordinator:
        store=Store()
        def status(self):return saved['refresh']
    monkeypatch.setattr(overview_refresh,'coordinator',Coordinator())
    monkeypatch.setattr(overview_refresh.economy_brief,'build_brief',lambda:pytest.fail('Do not rebuild or refresh data'))
    result=overview_refresh.read_brief()
    assert result['source_checks']['status']=='complete' and result['data_revision']=='saved'
    assert result['reading_comparisons']==saved['reading_comparisons'] and data==saved

def test_successful_source_cannot_hide_missing_displayed_event():
    data=brief();fed(data)['scope']['dates'].append('2026-10-29')
    result=scope_overview_checks(data)
    assert result['source_checks']['status']=='partial'
    assert fed(result)['overview_error_code']=='displayed_event_unavailable'
