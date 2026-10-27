"""Calendar event bindings are based on stored availability, never today's latest pair."""
from datetime import date,datetime,timezone
import copy
import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.analytics.calendar_readings import bind_events,linked_period
from app.analytics.calendar_agenda import validate_range,scoped_check
from app.analytics.overview_refresh import RefreshCoordinator
from tests.test_overview_refresh import MemoryStore,NOW

NOW=datetime(2026,10,26,12,tzinfo=timezone.utc)
def point(day,value,vintage='2026-09-11',end='9999-12-31'):
 return {'observation_date':day,'value':value,'vintage_date':vintage,'realtime_end':end}
def event(rid=10,day='2026-09-11',series=('CPIAUCSL','CPILFESL')):
 return {'release_id':rid,'release_date':day,'release_name':'A publication','release_datetime_utc':day+'T12:30:00Z',
 'series':[{'series_id':s,'short_name':s,'name':s,'frequency':'quarterly' if s=='GDPC1' else 'weekly' if s in ('ICSA','CCSA') else 'monthly','unit':'index'} for s in series]}
def cpi_panel():
 return {'CPIAUCSL':[point('2026-06-01',100,'2026-07-10'),point('2026-07-01',101,'2026-08-12'),point('2026-08-01',102)],
         'CPILFESL':[point('2026-06-01',100,'2026-07-10'),point('2026-07-01',102,'2026-08-12'),point('2026-08-01',103)]}

def test_publication_has_distinct_measure_rows_and_exact_transform_period():
 result=bind_events([event()],cpi_panel(),{},NOW)[0]
 assert len(result['measures'])==4
 mom=result['measures'][0]
 assert mom['reference_period']=='2026-08-01' and mom['previous_period']=='2026-07-01'
 assert mom['actual']==pytest.approx((102/101-1)*100)
 assert mom['previous']==pytest.approx(1)
 assert mom['data_version']=='stored_date_vintage' and mom['vintage_date']=='2026-09-11'
 assert result['measures'][1]['actual'] is None  # No year-ago denominator; never borrow MoM.
 assert all(m['forecast'] is None for m in result['measures'])


def test_future_release_and_passed_time_without_evidence_do_not_get_latest_pair():
 for day in ['2026-11-11','2026-10-14']:
  item=bind_events([event(day=day)],cpi_panel(),{'CPIAUCSL':[point('2026-08-01',102),point('2026-09-01',103)]},NOW)[0]['measures'][0]
  assert item['reference_period'] is None and item['actual'] is None and item['previous'] is None
  assert item['result_status']==('scheduled' if day>str(NOW.date()) else 'awaiting_data')


def test_today_before_confirmed_time_does_not_show_date_only_vintage():
 e=event(day='2026-10-26');panel={'CPIAUCSL':[point('2026-09-01',102,'2026-10-26')]}
 assert bind_events([e],panel,{},datetime(2026,10,26,10,tzinfo=timezone.utc))[0]['measures'][0]['actual'] is None


def test_shared_report_month_can_use_explicitly_labelled_current_vintage():
 e=event(50,'2026-10-02',('PAYEMS','UNRATE','CES0500000003'))
 panel={'PAYEMS':[point('2026-08-01',100,'2026-09-04'),point('2026-09-01',101,'2026-10-02')]}
 current={'CES0500000003':[point('2026-08-01',30),point('2026-09-01',31)]}
 wage=bind_events([e],panel,current,NOW)[0]['measures'][2]
 assert wage['reference_period']=='2026-09-01' and wage['binding_method']=='shared_report_month'
 assert wage['actual']==pytest.approx(100/30) and wage['data_version']=='current_vintage'
 assert not wage['revision_confirmed'] and wage['vintage_date'] is None


def test_claims_use_their_separate_weekly_reference_periods():
 e=event(180,'2026-10-08',('ICSA','CCSA'))
 panel={'ICSA':[point('2026-09-26',198000,'2026-10-01'),point('2026-10-03',199000,'2026-10-08')],
 'CCSA':[point('2026-09-19',1700000,'2026-10-01'),point('2026-09-26',1710000,'2026-10-08')]}
 items=bind_events([e],panel,{},NOW)[0]['measures']
 assert [m['reference_period'] for m in items]==['2026-10-03','2026-09-26']
 assert [m['previous_period'] for m in items]==['2026-09-26','2026-09-19']


def test_gdp_later_estimate_compares_same_quarter_vintages_and_proves_revision():
 rows=[point('2026-01-01',100,'2026-04-30'),point('2026-04-01',101,'2026-07-30','2026-09-29'),point('2026-04-01',102,'2026-09-30')]
 result=bind_events([event(53,'2026-09-30',('GDPC1',))],{'GDPC1':rows},{},NOW)[0]['measures'][0]
 assert result['previous_kind']=='previous_estimate' and result['previous_period']==result['reference_period']=='2026-04-01'
 assert result['actual']==pytest.approx((1.02**4-1)*100) and result['previous']==pytest.approx((1.01**4-1)*100)
 assert result['revision_confirmed'] and result['previous_data_version']=='stored_date_vintage'
 first=bind_events([event(53,'2026-07-30',('GDPC1',))],{'GDPC1':rows},{},NOW)[0]['measures'][0]
 assert first['previous_kind']=='previous_period' and first['previous_period']=='2026-01-01'


def test_missing_dot_expired_intervals_and_holes_remain_missing():
 panel=cpi_panel();panel['CPIAUCSL'][-1]['value']='.'
 result=bind_events([event()],panel,{},NOW)[0]['measures'][0]
 assert result['actual'] is None
 panel=cpi_panel();panel['CPIAUCSL'][1]['realtime_end']='2026-09-10'
 assert bind_events([event()],panel,{},NOW)[0]['measures'][0]['actual'] is None


def test_unknown_release_id_or_ambiguous_report_month_is_not_guessed():
 assert bind_events([event(999)],cpi_panel(),{},NOW)[0]['measures'][0]['reference_period'] is None
 e=event(50,'2026-10-02',('PAYEMS','UNRATE','CES0500000003'))
 panel={'PAYEMS':[point('2026-09-01',100,'2026-10-02')],'UNRATE':[point('2026-08-01',4,'2026-10-02')]}
 assert bind_events([e],panel,{},NOW)[0]['measures'][2]['reference_period'] is None


def test_later_vintages_do_not_leak_into_stored_historical_result():
 panel=cpi_panel();original=copy.deepcopy(panel)
 panel['CPIAUCSL'][-1]['realtime_end']='2026-09-30'
 panel['CPIAUCSL'].append(point('2026-08-01',200,'2026-10-01'))
 historical=bind_events([event()],panel,{},NOW)[0]['measures'][0]
 assert historical['actual']==pytest.approx((102/101-1)*100) and not historical['revision_confirmed']
 assert original['CPIAUCSL'][-1]['value']==102


def test_non_numerical_event_has_no_awaiting_reading():
 e=event(None,series=());e['event_type']='conference'
 result=bind_events([e],{}, {},NOW)[0]
 assert result['expects_numeric_result'] is False and result['measures']==[]


def test_calendar_range_limit_reversed_and_leap_year():
 validate_range(date(2024,1,1),date(2024,12,31))
 with pytest.raises(ValueError):validate_range(date(2024,1,1),date(2025,1,1))
 with pytest.raises(ValueError):validate_range(date(2026,11,1),date(2026,10,1))


def test_selected_range_registration_uses_same_coordinator_and_respects_cooldown(monkeypatch):
 store=MemoryStore();store.state.update(status='complete',completed_at=NOW,next_check_at=NOW.replace(hour=13))
 coordinator=RefreshCoordinator(store,lambda *a:pytest.fail('Cooldown must prevent a provider job'),lambda:NOW,lambda fn:fn())
 result=coordinator.request(date(2025,12,1),date(2025,12,31))
 assert result['status']=='complete' and store.state['source_versions']['calendar_requested_window']=={'start_date':'2025-12-01','end_date':'2025-12-31'}
 with pytest.raises(ValueError):coordinator.request(date(2026,1,1),None)


def test_rich_calendar_api_reuses_existing_endpoint(monkeypatch):
 from app.analytics import calendar_agenda
 monkeypatch.setattr(calendar_agenda,'calendar_agenda',lambda start,end,**kwargs:{'events':[],'start_date':start,'end_date':end,'check':{'status':'partial'}})
 response=TestClient(app).get('/api/v1/calendar?start_date=2026-10-26&end_date=2026-11-01&include_readings=true')
 assert response.status_code==200 and response.json()['check']['status']=='partial'


def test_range_scope_does_not_claim_success_for_another_checked_window():
 checks={'sources':[{'resource':'fred:calendar','label':'Releases','status':'success','coverage_checked_at':'2026-10-26T10:00:00Z','scope':{'start_date':'2026-10-01','end_date':'2026-12-31'}}]}
 result=scoped_check(checks,date(2025,10,1),date(2025,10,7),[],{'status':'available'})
 assert result['status']=='partial' and result['sources'][0]['scope_error']=='selected_range_not_checked'

def test_range_uses_previous_matching_scope_instead_of_latest_unrelated_window():
    checks={'sources':[{'resource':'fred:calendar','label':'Releases','status':'success','coverage_checked_at':'2026-10-26T10:00:00Z','scope':{'start_date':'2026-10-01','end_date':'2026-10-07'},'coverage_scope':{'start_date':'2026-10-01','end_date':'2026-12-31'}},
                      {'resource':'fed:calendar','label':'Fed','status':'success','coverage_checked_at':'2026-10-26T09:00:00Z','scope':{'dates':['2026-01-28','2027-12-08']}}]}
    result=scoped_check(checks,date(2026,11,1),date(2026,11,30),[],{'status':'available'})
    assert result['status']=='complete' and result['sources'][0]['checked_at']=='2026-10-26T10:00:00Z'


def test_scoped_calendar_distinguishes_distant_unpublished_times_from_displayed_failure():
    checks={'sources':[{'resource':'fred:calendar','label':'FRED','status':'success','coverage_checked_at':'2026-10-26T10:00:00Z','scope':{'start_date':'2026-10-01','end_date':'2026-12-31'}},
      {'resource':'fed:calendar','label':'Fed','status':'partial','error_code':'decision_times_unavailable','coverage_checked_at':'2026-10-26T09:00:00Z','last_finished_at':'2026-10-26T10:00:00Z','scope':{'dates':['2026-10-28','2027-12-08'],'missing_times':['2027-01-27'],'time_checks':[{'release_date':'2027-01-27','fetch_status':'success','time_status':'unconfirmed'}]}}]}
    shown={'release_id':None,'release_date':'2026-10-28','event_type':'fomc_decision','release_datetime_utc':'2026-10-28T18:00:00Z','series':[]}
    result=scoped_check(checks,date(2026,10,26),date(2026,11,1),[shown],{'status':'available'})
    assert result['status']=='complete' and result['sources'][1]['later_missing_times']==['2027-01-27']
    shown['release_datetime_utc']=None
    result=scoped_check(checks,date(2026,10,26),date(2026,11,1),[shown],{'status':'available'})
    assert result['status']=='partial' and result['sources'][1]['missing_times']==['2026-10-28']
    checks['sources'][1]['scope']['time_checks'].append({'release_date':'2026-10-28','fetch_status':'error','time_status':'unconfirmed'})
    assert scoped_check(checks,date(2026,10,26),date(2026,11,1),[shown],{'status':'available'})['status']=='error'
