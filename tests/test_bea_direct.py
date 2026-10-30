"""Offline BEA tests use small synthetic documents, never publisher snapshots."""
import copy
from datetime import datetime,timezone,timedelta,date
from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
from app.ingestion import sync_bea_reports as source
from app.analytics import bea_direct as binding

NOW=datetime(2026,10,30,12,tzinfo=timezone.utc)
URL='https://www.bea.gov/news/2026/synthetic-gdp'
PIO='https://www.bea.gov/news/2026/synthetic-pio'
PROOF=dict(release_id=53,reference_period='2026-07-01',estimate_stage='advance',release_date='2026-10-29',release_time='08:30:00')
P_PROOF=dict(release_id=54,reference_period='2026-09-01',estimate_stage=None,release_date='2026-10-29',release_time='08:30:00')

def heading(title):
    return f'<h1>{title}</h1><div class="release-embargo">EMBARGOED UNTIL RELEASE AT 8:30 a.m. EDT, Thursday, October 29, 2026</div>'

def gdp(value='1.2',previous='2.3'):
    return heading('GDP (Advance Estimate), 3rd Quarter 2026')+f'''<p>Real gross domestic product (GDP) increased at an annual rate of {value} percent in the third quarter of 2026. In the second quarter, real GDP increased {previous} percent.</p>
    <table><caption>Real GDP and Related Measures</caption><tr><th>Percent Change from 2026:Q2 to 2026:Q3 (Seasonally Adjusted Annual Rates (SAAR))</th></tr><tr><th>Advance Estimate</th></tr><tr><td>Real GDP</td><td>{value}</td></tr></table>'''

def pio(value='0.2',previous='0.1'):
    rows=''.join(f'<tr><td>{label}</td><td>{previous}</td><td>{value}</td></tr>' for label in ['PCE price index','PCE price index excluding food and energy','Real PCE','Real DPI'])
    return heading('Personal Income and Outlays, September 2026')+f'''<table><caption>Personal Income and Related Measures</caption><tr><th>Percent change from preceding month</th></tr><tr><th>August</th><th>September</th></tr>{rows}</table>
    <p>From the same month one year ago, the PCE price index increased 2.0 percent. Excluding food and energy, the PCE price index increased 2.4 percent from one year ago.</p>
    <p>The personal saving rate (personal saving as a percentage of DPI) was 4.2 percent.</p>'''

def schedule():
    return '<table><tr><th>Year 2026</th></tr>'+''.join(f'<tr><td>October 29 8:30 AM</td><td>News</td><td><a href="{url}">{title}</a></td></tr>' for url,title in [(URL,'GDP (Advance Estimate), 3rd Quarter 2026'),(PIO,'Personal Income and Outlays, September 2026')])+'</table>'

def run(path,connection,gdp_body=None,pio_body=None,now=NOW,status=200):
    def transport(request):
        url=str(request.url)
        return httpx.Response(200 if url==source.SCHEDULE else status,text=schedule() if url==source.SCHEDULE else gdp_body or gdp() if url==URL else pio_body or pio())
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        return source.sync_source(client,connection,now,Path(path))

def state(body=None):
    meta=source.parse_report(body or gdp(),PROOF,URL,NOW.isoformat())
    doc=dict(id='doc-1',source_url=URL,retrieved_at=NOW-timedelta(days=1),http_status=200,raw_hash='a'*64,kind=meta['identity'],metadata=meta)
    sid=source.storage_id('GDPC1','qoq_annualized','advance')
    return dict(documents=[doc],observations={(sid,'2026-07-01'):dict(value=meta['readings'][0]['value'],document_id='doc-1',publication_document_id='doc-1',vintage_date='2026-10-30')})

def measure():
    return dict(series_id='GDPC1',feature_name='qoq_annualized',frequency='quarterly',reference_period='2026-07-01',actual=1.234567,previous=2.345,previous_period='2026-04-01',previous_kind='previous_period',data_version='current_vintage',previous_data_version='current_vintage',source_url='https://fred.stlouisfed.org/series/GDPC1')

def test_own_actual_and_previous_are_published_not_fred_calculations():
    selected=binding.select(measure(),PROOF,state(),NOW)
    assert (selected['actual'],selected['previous'])==(1.2,2.3)
    assert selected['fred_alternative']['actual']==1.234567
    assert selected['source_comparison']=='consistent_with_rounding' and selected['data_version']=='official_release'
    assert selected['actual_provenance']['version']=='captured_snapshot' and selected['forecast'] is None
    assert selected['usage_rights']['terms_url']==source.TERMS

@pytest.mark.parametrize('stage',['second','third','updated'])
def test_each_gdp_stage_has_its_own_published_value(stage):
    proof={**PROOF,'estimate_stage':stage}
    body=gdp().replace('Advance Estimate',stage.title()+' Estimate')
    assert source.parse_report(body,proof,URL,NOW.isoformat())['readings'][0]['value']=='1.2'

def test_bea_only_and_no_document_fred_only_are_distinct():
    m=measure();m['actual']=None
    assert binding.select(m,PROOF,state(),NOW)['source_comparison']=='bea_only'
    assert binding.select(measure(),PROOF,dict(documents=[],observations={}),NOW)['selected_source']=='fred_fallback'

def test_direct_official_proof_does_not_require_fred_period_or_value():
    m=measure();m.update(reference_period=None,actual=None,previous=None)
    event=dict(release_id=53,release_date='2026-10-29')
    result=binding.select(m,event,state(),NOW)
    assert result['actual']==1.2 and result['reference_period']=='2026-07-01'
    assert result['actual_provenance']['estimate_stage']=='advance'

@pytest.mark.parametrize('status',[403,404,503])
def test_http_failure_is_partial_and_does_not_store_a_number(tmp_path,monkeypatch,status):
    from contextlib import contextmanager,nullcontext
    class Connection:
        def transaction(self):return nullcontext()
    calls=[]
    @contextmanager
    def check(*a,**k):yield {'status':'running','scope':{}}
    monkeypatch.setattr(source,'availability_check',check)
    monkeypatch.setattr(source,'store_report',lambda *a:calls.append(a))
    result=run(tmp_path,Connection(),status=status)
    assert result['status']=='partial' and len(result['errors'])==2 and not calls

def test_bea_attempt_precedes_fred_even_if_fred_cycle_cannot_continue(monkeypatch):
    from app.analytics import overview_refresh as refresh
    calls=[]
    monkeypatch.setattr(source,'sync_source',lambda *a,**k:calls.append('bea') or {'status':'success'})
    def stop(*a):
        assert calls==['bea']
        raise RuntimeError('Synthetic FRED inventory failure')
    monkeypatch.setattr(refresh,'inventory',stop)
    with pytest.raises(RuntimeError):refresh.refresh_sources(None,{},NOW)

def test_request_budget_exhaustion_stops_before_http(tmp_path,monkeypatch):
    from contextlib import contextmanager,nullcontext
    class Connection:
        def transaction(self):return nullcontext()
    @contextmanager
    def check(*a,**k):yield {'status':'running','scope':{}}
    monkeypatch.setattr(source,'availability_check',check)
    def exhausted(*a):raise TimeoutError('Synthetic budget expired')
    monkeypatch.setattr(source,'before_request',exhausted)
    with pytest.raises(TimeoutError):run(tmp_path,Connection())

@pytest.mark.parametrize('value',['0.0','-0.2','-9.4','2.5'])
def test_pio_zero_negative_and_precision(value):
    result=source.parse_report(pio(value),P_PROOF,PIO,NOW.isoformat())
    assert len(result['readings'])==6 and all(r['precision']==1 for r in result['readings'])
    assert result['readings'][0]['value']==value
    assert next(r for r in result['readings'] if r['series_id']=='PSAVERT')['method']=='published_level'
    assert next(r for r in result['readings'] if r['feature_name']=='yoy')['value']=='2.4'

@pytest.mark.parametrize('bad',['ND','NaN','inf','0.123','4','-1001.0'])
def test_malformed_published_number_is_not_zero(bad):
    with pytest.raises(ValueError):source.parse_report(pio(bad),P_PROOF,PIO,NOW.isoformat())

@pytest.mark.parametrize('old,new',[
 ('3rd Quarter 2026','2nd Quarter 2026'),('Advance Estimate','Second Estimate'),('Thursday','Friday'),('EDT','EST'),('8:30','9:30'),
 ('2026:Q3','2026:Q2'),('third quarter of 2026','second quarter of 2026'),('Seasonally Adjusted Annual Rates (SAAR)','Monthly changes')])
def test_mismatched_gdp_identity_or_units_are_rejected(old,new):
    with pytest.raises(ValueError):source.parse_report(gdp().replace(old,new),PROOF,URL,NOW.isoformat())

def test_same_quarter_previous_estimate_is_not_previous_quarter():
    html=gdp().replace('<th>Advance Estimate</th>','<th>Advance Estimate</th><th>Second Estimate</th>').replace('<td>1.2</td>','<td>1.2</td><td>9.9</td>')
    assert source.parse_report(html,PROOF,URL,NOW.isoformat())['readings'][0]['previous']=='2.3'

def test_conflicting_headline_and_table_fails():
    with pytest.raises(ValueError):source.parse_report(gdp().replace('<td>1.2</td>','<td>1.3</td>'),PROOF,URL,NOW.isoformat())

@pytest.mark.parametrize('url',['http://www.bea.gov/news/fake','https://other.example/news/fake','https://bea.gov/not-news/fake'])
def test_wrong_publisher_or_path(url):
    with pytest.raises(ValueError):source.parse_report(gdp(),PROOF,url,NOW.isoformat())

def test_missing_one_pio_measure_does_not_use_nominal_replacement():
    result=source.parse_report(pio().replace('Real PCE','Nominal PCE'),P_PROOF,PIO,NOW.isoformat())
    assert result['missing_measures']==['PCEC96:mom'] and len(result['readings'])==5

def test_missing_core_does_not_borrow_headline():
    result=source.parse_report(pio().replace('Excluding food and energy, the PCE price index increased','Unrelated prices increased'),P_PROOF,PIO,NOW.isoformat())
    assert 'PCEPILFE:yoy' in result['missing_measures']

def test_wrong_month_and_ambiguous_summary_rejected():
    for body in [pio().replace('September 2026','August 2026'),pio()+pio()]:
        with pytest.raises(ValueError):source.parse_report(body,P_PROOF,PIO,NOW.isoformat())

def test_source_conflict_keeps_bea_and_both_provenances():
    m=measure();m['actual']=9.9;r=binding.select(m,PROOF,state(),NOW)
    assert r['actual']==1.2 and r['source_comparison']=='conflict' and r['fred_alternative']['actual']==9.9

@pytest.mark.parametrize('alternative,expected',[
    ('1.15','consistent_with_rounding'),('1.25','consistent_with_rounding'),
    ('1.1500000000000001','consistent_with_rounding'),('1.2499999999999999','consistent_with_rounding'),
    ('1.1499999999999999','conflict'),('1.2500000000000001','conflict')])
def test_rounding_tolerance_includes_exact_boundary_without_float_subtraction(alternative,expected):
    from decimal import Decimal
    m=measure();m['actual']=Decimal(alternative)
    assert binding.select(m,PROOF,state(),NOW)['source_comparison']==expected

def test_later_fred_snapshot_stays_separate_from_confirmed_bea():
    m=measure();m.update(actual=4.5,actual_provenance={'source':'fred_snapshot','vintage_date':'2026-10-30','retrieved_at':NOW.isoformat()})
    result=binding.select(m,PROOF,state(),NOW)
    assert result['actual']==1.2 and result['actual_provenance']['source']=='bea_official'
    assert result['fred_alternative']['actual']==4.5 and result['fred_alternative']['actual_provenance']==m['actual_provenance']

def test_a_report_not_yet_captured_does_not_create_actual():
    m=measure();m['actual']=None
    result=binding.select(m,PROOF,dict(documents=[],observations={}),NOW)
    assert result['actual'] is None and result['selected_source']=='not_available'

@pytest.mark.parametrize('field,value',[('release_date','2026-11-25'),('reference_period','2026-04-01'),('estimate_stage','second')])
def test_other_event_never_borrows_direct_value(field,value):
    event={**PROOF,field:value};r=binding.select(measure(),event,state(),NOW)
    assert r['actual']==1.234567 and r['selected_source']=='fred_fallback'

@pytest.mark.parametrize('mutation',['no_sql','wrong_fk','wrong_publication_fk','wrong_value','future_capture','future_embargo'])
def test_receipt_without_confirmed_sql_or_future_document_cannot_create_actual(mutation):
    s=state();point=next(iter(s['observations'].values()))
    if mutation=='no_sql':s['observations']={}
    elif mutation=='wrong_fk':point['document_id']='other'
    elif mutation=='wrong_publication_fk':point['publication_document_id']='other'
    elif mutation=='wrong_value':point['value']='5.0'
    elif mutation=='future_capture':s['documents'][0]['retrieved_at']=NOW+timedelta(days=1)
    else:s['documents'][0]['metadata']['announced_at']=(NOW+timedelta(days=1)).isoformat()
    assert binding.select(measure(),PROOF,s,NOW)['selected_source']=='fred_fallback'

def test_previous_missing_is_explicit_fallback_without_mixed_difference():
    s=state();s['documents'][0]['metadata']['readings'][0]['previous']=None
    r=binding.select(measure(),PROOF,s,NOW)
    assert r['previous']==2.345 and r['comparison_status']=='mixed_sources' and r['previous_precision'] is None

def test_discovery_retains_existing_event_identities_and_links():
    rows=source.discover(schedule(),NOW.isoformat())
    assert len(rows)==2 and {r['report_url'] for r in rows}=={URL,PIO}
    assert {source.key(r) for r in rows}=={'53:2026-07-01:advance:2026-10-29','54:2026-09-01:monthly:2026-10-29'}

def test_explicit_schedule_clock_is_not_replaced_with_eight_thirty():
    rows=source.discover(schedule().replace('8:30 AM','10:00 AM'),NOW.isoformat())
    proof=next(r for r in rows if r['release_id']==54)
    assert proof['release_time']=='10:00:00'
    assert source.parse_report(pio().replace('8:30 a.m.','10:00 a.m.'),proof,PIO,NOW.isoformat())['announced_at']=='2026-10-29T14:00:00+00:00'

def test_saving_and_annual_previous_not_borrowed_from_prior_document():
    rows=source.parse_report(pio(),P_PROOF,PIO,NOW.isoformat())['readings']
    assert all(r['previous'] is None for r in rows if r['feature_name']=='yoy' or r['series_id']=='PSAVERT')

def test_overview_prefers_published_rate_without_changing_classification(monkeypatch):
    monkeypatch.setattr(binding,'load_state',lambda c:state())
    item=dict(series_id='GDPC1',feature_name='qoq_annualized',frequency='quarterly',current=dict(value=1.2345,observation_date='2026-07-01'),previous=dict(value=2.3,observation_date='2026-04-01'),expected_previous_observation_date='2026-04-01',domain='growth',component='real_gdp')
    rows=binding.overview([item],None,date(2026,10,30))
    assert rows[0]['current']['value']==1.2 and rows[0]['change']==-1.1 and rows[0]['component']=='real_gdp'
