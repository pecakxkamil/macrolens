"""Free publisher adapters and result availability; entirely offline fixtures."""
import copy
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo
import pytest

from app.ingestion.sync_calendar_periods import parse_retail_schedule,parse_g17_schedule,parse_g17_report,parse_retail_report
from app.analytics.release_times import release_time_metadata
from app.analytics.calendar_readings import bind_events
from app.analytics.release_calendar import apply_bls_schedule
from tests.test_calendar_agenda import event,point

STAMP='2026-10-27T12:22:58+00:00'
METHOD='<p>The G.17 release and the supplement to the release are published about 15 days after the reference month ends; for example, preliminary estimates for May are released in mid-June.</p>'
G17='<h5>The monthly releases are issued at 9:15 a.m. The annual revision is issued at noon.</h5><p>2026: October 16 (most recent monthly), November 17, November 24 (annual revision), and December 16.</p><p>2027: January 15, February 17.</p>'
RETAIL='<h2>Advance Monthly Retail Trade Report</h2><table><tr><th>Data Month</th><th>Release Date at 8:30 am</th></tr><tr><td>September 2026</td><td>October 15, 2026</td></tr><tr><td>October 2026</td><td>November 17, 2026</td></tr><tr><td>December 2026</td><td>January 15, 2027</td></tr><tr><td>December 2027</td><td>To be announced at a later date</td></tr></table><h2>Monthly Retail Trade Report</h2><table><tr><td>August 2026</td><td>October 15, 2026</td></tr></table>'
G17_REPORT='<div class="dates">Release Date: October 16, 2026</div><p>Industrial production (IP) increased 0.7 percent in September after edging up 0.1 percent in August. Capacity utilization moved up in September.</p><table title="Industrial Production and Capacity Utilization: Summary"><tr><th>2026</th><th>2026</th></tr></table>'
RETAIL_REPORT='<h4>FOR IMMEDIATE RELEASE: Thursday, October 15, 2026</h4><p>Advance estimates of U.S. retail and food services sales for September 2026 were higher.</p>'


def test_retail_only_advance_table_and_explicit_months_cross_year():
    rows=parse_retail_schedule(RETAIL,'retail',STAMP)
    assert [(r['release_date'],r['reference_period']) for r in rows]==[('2026-10-15','2026-09-01'),('2026-11-17','2026-10-01'),('2027-01-15','2026-12-01')]
    assert all(r['estimate_stage']=='advance' and r['release_time']=='08:30:00' for r in rows)
    with pytest.raises(ValueError):parse_retail_schedule(RETAIL.replace('<td>October 2026</td>','<td>October and November 2026</td>'),'retail',STAMP)
    with pytest.raises(ValueError):parse_retail_schedule(RETAIL.replace('8:30 am','9:00 am'),'retail',STAMP)


def test_g17_documented_monthly_rule_and_annual_exception():
    rows,rules=parse_g17_schedule(G17,'g17',STAMP,METHOD)
    assert [(r['release_date'],r['reference_period']) for r in rows]==[('2026-10-16','2026-09-01'),('2026-11-17','2026-10-01'),('2026-12-16','2026-11-01'),('2027-01-15','2026-12-01'),('2027-02-17','2027-01-01')]
    assert all(r['series_ids']==['INDPRO','TCU'] and r['rule_source_url'].endswith('OMB_2026.htm') for r in rows)
    assert rules[0]['dates']['2026-11-24']=='12:00:00'
    assert not any(r['release_date']=='2026-11-24' for r in rows)
    assert parse_g17_schedule(G17,'g17',STAMP,None)[0]==[]
    delayed=G17.replace('October 16 (most recent monthly)','October 26 (delayed)')
    assert not any(r['release_date']=='2026-10-26' for r in parse_g17_schedule(delayed,'g17',STAMP,METHOD)[0])


def test_g17_missing_schedule_or_clock_cannot_create_records():
    for html in ('<h1>Unavailable</h1>',G17.replace('9:15','10:00')):
        with pytest.raises(ValueError):parse_g17_schedule(html,'g17',STAMP,METHOD)


def test_g17_shared_report_period_and_independent_result_availability():
    proof=parse_g17_report(G17_REPORT,'report',STAMP)
    assert proof['reference_period']=='2026-09-01' and proof['series_ids']==['INDPRO','TCU']
    evidence={'periods':[proof],'results':[proof]};e=event(13,'2026-10-16',('INDPRO','TCU'))
    rows={'INDPRO':[point('2026-08-01',100,'2026-10-16'),point('2026-09-01',101,'2026-10-16')],
          'TCU':[point('2026-08-01',76.4,'2026-10-16')]}
    after=datetime(2026,10,17,tzinfo=timezone.utc);updates={'INDPRO':'2026-10-16','TCU':'2026-10-16'}
    result=bind_events([e],{},rows,after,evidence,updates)[0]['measures']
    assert [m['reference_period'] for m in result]==['2026-09-01']*2
    assert result[0]['actual']==pytest.approx(1) and result[1]['actual'] is None
    assert result[1]['previous']==76.4
    rows['TCU'].append(point('2026-09-01',76.9,'2026-10-16'))
    result=bind_events([e],{},rows,after,evidence,updates)[0]['measures']
    assert result[1]['actual']==76.9 and result[1]['feature_name']=='raw' and result[1]['unit']=='percent'
    assert all(m['data_version']=='current_vintage' and not m['revision_confirmed'] for m in result)


def test_report_clock_is_explicit_never_a_default_over_an_exception():
    assert parse_g17_report(G17_REPORT,'report',STAMP)['release_time'] is None
    assert parse_g17_report('<p>For release at 10:15 a.m.</p>'+G17_REPORT,'report',STAMP)['release_time']=='10:15:00'


def test_g17_report_spanning_two_years_uses_explicit_header_associations():
    report=G17_REPORT.replace('October 16, 2026','February 17, 2027').replace('September','January')
    report=report.replace('<th>2026</th><th>2026</th>','<th id="prior">2026</th><th id="latest">2027</th><th id="jan"><abbr title="january">Jan.</abbr></th></tr><tr><td headers="latest jan">105.0</td>')
    assert parse_g17_report(report,'report',STAMP)['reference_period']=='2027-01-01'


def test_retail_report_requires_new_fetched_values_and_correct_receipt():
    proof=parse_retail_schedule(RETAIL,'retail',STAMP)[0];receipt=parse_retail_report(RETAIL_REPORT,'report',STAMP)
    evidence={'periods':[proof]};e=event(9,'2026-10-15',('RSAFS',));updates={'RSAFS':'2026-10-15'}
    rows={'RSAFS':[point('2026-07-01',100,'2026-10-10'),point('2026-08-01',101,'2026-10-10'),point('2026-09-01',103,'2026-10-10')]}
    after=datetime(2026,10,16,tzinfo=timezone.utc)
    def measure():return bind_events([e],{},rows,after,evidence,updates)[0]['measures'][0]
    assert measure()['actual'] is None
    evidence['results']=[receipt];assert measure()['actual'] is None
    rows['RSAFS']=[dict(p,vintage_date='2026-10-15') for p in rows['RSAFS']]
    assert measure()['actual']==pytest.approx((103/101-1)*100) and measure()['previous']==pytest.approx(1)


@pytest.mark.parametrize('rid,sids,name,clock',[(9,('RSAFS',),'Advance Monthly Sales for Retail and Food Services','08:30:00'),(13,('INDPRO','TCU'),'G.17 Industrial Production and Capacity Utilization','09:15:00'),(192,('JTSJOL',),'Job Openings and Labor Turnover Survey','10:00:00'),(46,('PPIFIS',),'Producer Price Index','08:30:00'),(11,('ECIALLCIV',),'Employment Cost Index','08:30:00')])
def test_future_result_and_consensus_stay_empty_with_correct_previous(rid,sids,name,clock):
    day='2026-11-17';period='2026-10-01';previous='2026-09-01';earlier='2026-08-01'
    if rid==11:period='2026-07-01';previous='2026-04-01';earlier='2026-01-01'
    proof=dict(release_id=rid,series_ids=list(sids),release_date=day,reference_period=period,release_time=clock,source_url='publisher',retrieved_at=STAMP,binding_method='official_schedule')
    evidence={'periods':[proof]};e=event(rid,day,sids);e.update(release_time_metadata(name,date.fromisoformat(day),evidence))
    if rid==11:e['series'][0]['frequency']='quarterly'
    rows={sid:[point(earlier,100),point(previous,101)] for sid in sids}
    result=bind_events([e],{},rows,datetime(2026,10,27,tzinfo=timezone.utc),evidence)[0]['measures']
    assert all(m['actual'] is None and m['forecast'] is None and m['previous'] is not None for m in result)
    assert all(m['previous_period']==previous for m in result)


@pytest.mark.parametrize('day,expected',[('2026-03-12','14:15'),('2026-10-29','14:15'),('2026-11-17','15:15')])
def test_g17_iana_time_and_explicit_exception_wins(day,expected):
    proof=dict(release_id=13,series_ids=['INDPRO','TCU'],release_date=day,reference_period='2026-09-01',release_time='09:15:00',source_url='report',retrieved_at=STAMP,binding_method='official_release')
    ev={'periods':[proof],'rules':[dict(release_id=13,valid_from='2026-01-01',valid_through='2026-12-31',dates={day:'12:00:00'},retrieved_at=STAMP,source_url='schedule')]}
    instant=release_time_metadata('G.17 Industrial Production and Capacity Utilization',date.fromisoformat(day),ev)['release_datetime_utc']
    assert datetime.fromisoformat(instant.replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==expected


def test_retail_moved_date_reuses_existing_calendar_overlay():
    old=parse_retail_schedule(RETAIL,'retail',STAMP)[1];moved={**old,'release_date':'2026-11-18'}
    ev={'periods':[moved],'publisher_history':[old]};events={(9,date(2026,11,17)):dict()}
    templates={9:dict(release_id=9,release_name='Advance Monthly Sales for Retail and Food Services',series=[])}
    apply_bls_schedule(events,templates,ev,date(2026,11,1),date(2026,11,30))
    assert list(events)==[(9,date(2026,11,18))]


def test_jolts_provider_timestamp_cannot_relabel_an_old_snapshot():
    proof=dict(release_id=192,series_ids=['JTSJOL'],release_date='2026-11-03',reference_period='2026-09-01',source_url='publisher',retrieved_at=STAMP,binding_method='reviewed_official_schedule')
    e=event(192,'2026-11-03',('JTSJOL',));evidence={'periods':[proof]}
    rows={'JTSJOL':[point('2026-08-01',7079,'2026-10-27'),point('2026-09-01',7000,'2026-10-27')]}
    now=datetime(2026,11,4,tzinfo=timezone.utc);updates={'JTSJOL':'2026-11-03'}
    assert bind_events([e],{},rows,now,evidence,updates)[0]['measures'][0]['actual'] is None
    rows['JTSJOL'][-1]['vintage_date']='2026-11-03'
    result=bind_events([e],{},rows,now,evidence,updates)[0]['measures'][0]
    assert result['actual']==7000 and result['previous']==7079 and result['data_version']=='current_vintage'
