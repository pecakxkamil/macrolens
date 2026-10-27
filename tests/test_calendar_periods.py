"""Offline publisher fixtures; no provider calls or real database required."""
from datetime import date, datetime, timezone
import copy
import pytest
from app.ingestion.sync_calendar_periods import parse_schedule, parse_decision, parsed_date
from app.analytics.calendar_evidence import period_evidence
from app.analytics.calendar_readings import bind_events
from tests.test_calendar_agenda import event,point,NOW


def evidence(rid,day,period,sids,stage=None):
    return {'periods':[dict(release_id=rid,release_date=day,reference_period=period,series_ids=list(sids),
        binding_method='official_schedule',source_url='https://www.bea.gov/news/schedule/full',retrieved_at=NOW.isoformat(),estimate_stage=stage)]}


def test_delayed_month_and_future_previous_never_use_latest_pair():
    e=event(54,'2026-10-29',('PCEPI',))
    proof=evidence(54,'2026-10-29','2026-08-01',('PCEPI',))
    rows=[point('2026-06-01',100),point('2026-07-01',101),point('2026-08-01',105),point('2026-09-01',109)]
    m=bind_events([e],{}, {'PCEPI':rows},NOW,proof)[0]['measures'][0]
    assert m['actual'] is None and m['previous']==pytest.approx(1)
    assert m['reference_period']=='2026-08-01' and m['previous_period']=='2026-07-01'
    assert m['previous_data_version']=='current_vintage' and m['previous_provenance']['observation_period']=='2026-07-01'
    assert m['missing_reason']['actual']=='not_yet_published'


def test_official_period_allows_explicit_current_vintage_after_publication():
    e=event(46,'2026-10-15',('PPIFIS',))
    rows=[point('2026-07-01',100),point('2026-08-01',101),point('2026-09-01',103)]
    m=bind_events([e],{}, {'PPIFIS':rows},NOW,evidence(46,'2026-10-15','2026-09-01',('PPIFIS',)))[0]['measures'][0]
    assert m['actual']==pytest.approx((103/101-1)*100) and m['previous']==pytest.approx(1)
    assert m['data_version']=='current_vintage' and not m['revision_confirmed']
    assert m['period_provenance']['source_url'].startswith('https://')


def test_missing_observation_and_dependency_are_different_reasons():
    e=event(10,'2026-10-14',('CPIAUCSL',));proof=evidence(10,'2026-10-14','2026-09-01',('CPIAUCSL',))
    m=bind_events([e],{}, {},NOW,proof)[0]['measures'][0]
    assert m['missing_reason']['actual']=='observation_missing'
    m=bind_events([e],{}, {'CPIAUCSL':[point('2026-09-01',103)]},NOW,proof)[0]['measures'][0]
    assert m['missing_reason']['actual']=='transformation_dependency_missing'


def test_elapsed_revised_permits_release_cannot_reuse_an_old_current_snapshot():
    e=event(27,'2026-10-27',('PERMIT',));proof=evidence(27,'2026-10-27','2026-09-01',('PERMIT',),'revised_permits')
    rows={'PERMIT':[point('2026-08-01',1403),point('2026-09-01',1400)]}
    now=datetime(2026,10,28,tzinfo=timezone.utc)
    m=bind_events([e],{},rows,now,proof,{'PERMIT':'2026-10-20 07:33:50-05'})[0]['measures'][0]
    assert m['actual'] is None and m['previous']==1403
    assert m['missing_reason']['actual']=='publication_stage_unconfirmed'
    m=bind_events([e],{},rows,now,proof,{'PERMIT':'2026-10-27 07:33:50-05'})[0]['measures'][0]
    assert m['actual'] is None  # A timestamp alone still does not prove the revision.
    proof['results']=[dict(proof['periods'][0],announced_at='2026-10-27T12:00:00+00:00')]
    rows['PERMIT'][-1]['vintage_date']='2026-10-27'
    m=bind_events([e],{},rows,now,proof,{'PERMIT':'2026-10-27 07:33:50-05'})[0]['measures'][0]
    assert m['actual']==1400 and m['data_version']=='current_vintage'


def test_revised_permits_published_value_must_match_provider_and_previous_stays_previous_month():
    e=event(27,'2026-10-27',('PERMIT',));proof=evidence(27,'2026-10-27','2026-09-01',('PERMIT',),'revised_permits')
    receipt={**proof['periods'][0],'reported_value':1398};proof['results']=[receipt]
    rows={'PERMIT':[point('2026-08-01',1403,'2026-10-27'),point('2026-09-01',1400,'2026-10-27')]}
    now=datetime(2026,10,27,14,tzinfo=timezone.utc)
    def reading():return bind_events([e],{},rows,now,proof,{'PERMIT':'2026-10-27'})[0]['measures'][0]
    m=reading();assert m['actual'] is None and m['missing_reason']['actual']=='revised_permits_provider_pending'
    assert m['publication_provenance']['reported_value']==1398
    rows['PERMIT'][-1]['value']=1398
    m=reading();assert m['actual']==1398 and m['previous']==1403
    assert m['previous_kind']=='previous_period' and m['previous_period']=='2026-08-01' and not m['revision_confirmed']
    # An unchanged revised number is still available when publication and fresh
    # provider data confirm it; a numerical change is not a prerequisite.
    receipt['reported_value']=1400;rows['PERMIT'][-1]['value']=1400
    assert reading()['actual']==1400


def test_revised_permits_clock_comes_from_its_own_schedule_header():
    from app.analytics.release_times import release_time_metadata
    html='<table><tr><th>Survey Month</th><th>New Residential Construction - 8:30 a.m.</th><th>Revised Building Permits - 8:00 a.m. New Residential Sales - 10:00 a.m.</th></tr><tr><td>September 2026</td><td>October 20, 2026</td><td>October 27, 2026</td></tr></table>'
    rows=parse_schedule('soc',html,'https://www.census.gov/construction/soc/schedule.html',NOW.isoformat())
    metadata=release_time_metadata('New Residential Construction',date(2026,10,27),{'periods':rows})
    assert metadata['release_time']=='08:00:00' and metadata['release_datetime_utc']=='2026-10-27T12:00:00Z'


def test_conflicting_and_other_series_evidence_cannot_bind_period():
    proof=evidence(10,'2026-10-14','2026-09-01',('CPIAUCSL',))
    proof['periods']+=evidence(10,'2026-10-14','2026-08-01',('CPIAUCSL',))['periods']
    assert period_evidence(proof,10,'2026-10-14','CPIAUCSL') is None
    assert period_evidence(proof,10,'2026-10-14','CPILFESL') is None
    assert bind_events([event(day='2026-10-14')],{}, {},NOW,proof)[0]['measures'][0]['reference_period'] is None


def test_revised_permits_does_not_present_another_housing_starts_measure():
    e=event(27,'2026-10-27',('HOUST','PERMIT'))
    proof=evidence(27,'2026-10-27','2026-09-01',('PERMIT',),'revised_permits')
    assert [m['series_id'] for m in bind_events([e],{}, {},NOW,proof)[0]['measures']]==['PERMIT']


def test_future_gdp_second_estimate_does_not_fall_back_to_previous_quarter():
    e=event(53,'2026-11-25',('GDPC1',))
    proof=evidence(53,'2026-11-25','2026-07-01',('GDPC1',),'second')
    m=bind_events([e],{}, {'GDPC1':[point('2026-01-01',100),point('2026-04-01',101)]},NOW,proof)[0]['measures'][0]
    assert m['previous_kind']=='previous_estimate' and m['previous_period']=='2026-07-01'
    assert m['actual'] is None and m['previous'] is None


def test_gdp_first_estimate_compares_previous_quarter_even_if_current_snapshot_has_that_quarter():
    e=event(53,'2026-10-29',('GDPC1',));proof=evidence(53,'2026-10-29','2026-07-01',('GDPC1',),'advance')
    panel={'GDPC1':[point('2026-01-01',100,'2026-04-30'),point('2026-04-01',101,'2026-09-30')]}
    m=bind_events([e],panel,{},NOW,proof)[0]['measures'][0]
    assert m['previous_kind']=='previous_period' and m['previous_period']=='2026-04-01'


def test_parser_keeps_explicit_dates_holiday_delays_and_estimate_stages():
    bea='<table><tr><th>Year 2026</th></tr><tr><td>October 29 8:30 AM</td><td>News</td><td>GDP (Advance Estimate), 3rd Quarter 2026</td></tr><tr><td>November 25 8:30 AM</td><td>News</td><td>GDP (Second Estimate), 3rd Quarter 2026</td></tr><tr><td>January 22 10:00 AM</td><td>News</td><td>Personal Income and Outlays, October and November 2025</td></tr></table>'
    rows=parse_schedule('bea',bea,'https://www.bea.gov/',NOW.isoformat())
    assert [(r['release_date'],r['reference_period'],r['estimate_stage']) for r in rows]==[('2026-10-29','2026-07-01','advance'),('2026-11-25','2026-07-01','second')]
    chicago='<table><tr><th>National Financial Conditions Index\n (NFCI)</th></tr><tr><td>November 12, 2026</td><td>November 6, 2026</td></tr></table>'
    assert parse_schedule('chicago',chicago,'https://www.chicagofed.org/',NOW.isoformat())[0]['reference_period']=='2026-11-06'
    with pytest.raises(ValueError):parse_schedule('bea','<h1>Unavailable</h1>','https://www.bea.gov/',NOW.isoformat())


def test_bls_and_census_adapters_use_only_explicit_table_periods():
    bls='<table><tr><td>Friday, November 6, 2026</td><td>08:30 AM</td><td>Employment Situation for October 2026</td></tr></table>'
    assert parse_schedule('bls',bls,'https://www.bls.gov/',NOW.isoformat())[0]['reference_period']=='2026-10-01'
    census='<table><tr><td>September 2026</td><td>October 20, 2026</td><td>October 27, 2026</td></tr></table>'
    rows=parse_schedule('soc',census,'https://www.census.gov/',NOW.isoformat())
    assert [(r['release_id'],r['series_ids']) for r in rows]==[(27,['HOUST','PERMIT']),(27,['PERMIT']),(97,['HSN1F'])]
    m3='<table><tr><td>August 2026</td><td>9/25/2026</td><td>10/2/2026</td></tr></table>'
    assert [r['estimate_stage'] for r in parse_schedule('m3',m3,'https://www.census.gov/',NOW.isoformat())]==['advance','full']


def test_policy_statement_and_effective_date_are_separate():
    result=parse_decision('<p>The Committee decided to raise the target range for the federal funds rate by 1/4 percentage point to 3-3/4 to 4 percent.</p>',
        '<p>Effective September 17, 2026, the Committee directs the Desk.</p>','2026-09-16','https://www.federalreserve.gov/statement','https://www.federalreserve.gov/implementation',NOW.isoformat())
    assert result['lower']==3.75 and result['upper']==4 and result['effective_date']=='2026-09-17'
    with pytest.raises(ValueError):parse_decision('<p>Meeting scheduled</p>','Effective September 17, 2026','2026-09-16','','',NOW.isoformat())


def test_claims_pdf_uses_distinct_explicit_weeks_and_year_rollover(monkeypatch):
    from types import SimpleNamespace
    import pypdf
    from app.ingestion.sync_calendar_periods import parse_claims
    text='Thursday, January 7, 2027. In the week ending January 2, the advance figure for seasonally adjusted initial claims was 200,000. The advance number for seasonally adjusted insured unemployment during the week ending December 26 was 1,700,000.'
    monkeypatch.setattr(pypdf,'PdfReader',lambda stream:SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda:text)]))
    rows=parse_claims(b'fixture','https://oui.doleta.gov/press/2027/010727.pdf',NOW.isoformat())
    assert [(r['series_ids'],r['reference_period']) for r in rows]==[(['ICSA'],'2027-01-02'),(['CCSA'],'2026-12-26')]


def test_future_or_elapsed_fomc_time_without_statement_never_proves_a_decision():
    prior=dict(release_date='2026-09-16',lower=3.75,upper=4,effective_date='2026-09-17',source_url='https://www.federalreserve.gov/statement')
    e=event(None,'2026-10-28',());e['event_type']='fomc_decision'
    proof={'decisions':[prior]}
    for now in [NOW,datetime(2026,10,29,tzinfo=timezone.utc)]:
        m=bind_events([e],{}, {},now,proof)[0]['measures'][0]
        assert m['actual'] is None and m['previous_range']==[3.75,4]
        assert m['previous_kind']=='previous_decision' and m['previous_effective_date']=='2026-09-17'
    proof['decisions'] += [dict(prior,release_date='2026-10-28',announced_at='2026-10-28T18:00:00+00:00',effective_date='2026-10-29',lower=3.5,upper=3.75)]
    m=bind_events([e],{}, {},datetime(2026,10,29,tzinfo=timezone.utc),proof)[0]['measures'][0]
    assert m['actual_range']==[3.5,3.75] and m['data_version']=='official_release'


def test_stored_official_statement_does_not_leak_before_its_announcement_time():
    e=event(None,'2026-10-28',());e['event_type']='fomc_decision'
    statement=dict(release_date='2026-10-28',announced_at='2026-10-28T18:00:00+00:00',lower=3.75,upper=4,effective_date='2026-10-29',source_url='https://www.federalreserve.gov/statement')
    before=bind_events([e],{}, {},datetime(2026,10,28,17,tzinfo=timezone.utc),{'decisions':[statement]})[0]['measures'][0]
    assert before['actual'] is None
    after=bind_events([e],{}, {},datetime(2026,10,28,19,tzinfo=timezone.utc),{'decisions':[statement]})[0]['measures'][0]
    assert after['actual_range']==[3.75,4]


def test_failed_publisher_refresh_keeps_prior_evidence_and_records_failures(tmp_path,monkeypatch):
    import json
    import httpx
    from contextlib import contextmanager
    from app.ingestion import sync_calendar_periods as sync
    from app.analytics import fomc_calendar
    path=tmp_path/'derived'/'periods.json';path.parent.mkdir()
    old=evidence(95,'2026-10-27','2026-09-01',('DGORDER',))
    path.write_text(json.dumps({'version':1,**old}),encoding='utf-8')
    recorded={}
    @contextmanager
    def check(resource,scope):
        recorded.update(resource=resource,scope=scope)
        yield recorded
    monkeypatch.setattr(sync,'availability_check',check)
    monkeypatch.setattr(fomc_calendar,'read_schedule',lambda:{'events':[]})
    monkeypatch.setattr('app.ingestion.bls_schedule.time.sleep',lambda delay:None)
    transport=httpx.MockTransport(lambda request:httpx.Response(503,request=request))
    with httpx.Client(transport=transport) as client:
        result=sync.sync_periods(client,date(2026,10,26),date(2026,11,1),[],NOW,path)
    assert result['periods']==old['periods'] and len(result['checks'])==14
    assert all(c['status']=='error' for c in result['checks'])
    assert recorded['status']=='partial' and recorded['error_code']=='publisher_source_unavailable'
    assert json.loads(path.read_text(encoding='utf-8'))['periods']==old['periods']
