import copy
import json
from datetime import datetime,timezone
import pytest
from app import earnings_reports as r


def records():return json.loads(r.DATA.read_text(encoding='utf-8'))
def apple():return next(x for x in records() if x['ticker']=='AAPL')
def event():
    unknown=dict(date_status='unknown',precision='unknown',source_local_date=None,scheduled_at_utc=None)
    return dict(release={**unknown,'date_status':'confirmed','precision':'date_only','source_local_date':'2026-11-02','source_timezone':'America/Los_Angeles'},call=unknown,revenue_actual=None,reported_eps_actual=None)


def test_all_reviewed_sources_scope():
    rows=records();assert len(rows)==27
    assert sum(x['document']['document_type']=='earnings_release' for x in rows)==23
    assert sum(len(x['observations']) for x in rows)==46
    for x in rows:r.validate(x)


@pytest.mark.parametrize('mutation',[
 lambda x:x.update(cik='0001045810'),lambda x:x.update(fiscal_year=2025),lambda x:x.update(fiscal_quarter=1),
 lambda x:x.update(period_label='Q1 FY2027'),lambda x:x.update(period_end='2026-09-30'),
 lambda x:x.update(forecast=1),lambda x:x['document'].update(source_url='https://investing.com/release'),
 lambda x:x['document'].update(source_url='https://www.sec.gov/Archives/edgar/data/1/report.htm'),
 lambda x:x['document'].update(verification_method='http_200'),
 lambda x:x['document'].update(document_type='earnings_date_announcement'),
 lambda x:x['document'].update(reporting_currency='EUR'),lambda x:x['document'].update(reporting_standard='IFRS'),
 lambda x:x['observations'][1].update(methodology='non_gaap_adjusted'),
 lambda x:x['observations'][1].update(methodology='basic_eps'),lambda x:x['observations'][1].update(share_basis='ADR'),
 lambda x:x['observations'][1].update(currency='TWD'),lambda x:x['observations'][0].update(source_unit='thousands'),
 lambda x:x['observations'][0].update(source_value='NaN'),lambda x:x['observations'][0].update(source_value='-1'),
 lambda x:x['observations'][0].update(source_value=114477),lambda x:x['observations'][1].update(source_value='1.234'),
 lambda x:x['observations'].append(copy.deepcopy(x['observations'][0])),
])
def test_invalid_reports(mutation):
    x=apple();mutation(x)
    with pytest.raises(ValueError):r.validate(x)


@pytest.mark.parametrize('value',['0.00','-2.16'])
def test_zero_negative_eps(value):
    x=apple();x['observations'][1]['source_value']=value
    assert r.validate(x)['observations'][1]['source_value']==value


def test_ifrs_twd_ordinary_not_adr_or_usd():
    x=next(x for x in records() if x['ticker']=='TSM')
    assert r.validate(x)['observations'][1]['share_basis']=='ordinary_share'
    for field,value in [('currency','USD'),('reporting_standard','US_GAAP'),('share_basis','ADR')]:
        bad=copy.deepcopy(x);bad['observations'][1][field]=value
        with pytest.raises(ValueError):r.validate(bad)
    asml=next(x for x in records() if x['ticker']=='ASML')
    assert r.validate(asml)['document']['reporting_standard']=='US_GAAP'
    assert asml['document']['reporting_currency']=='EUR'


def test_publication_proof_can_precede_financial_basis_review():
    x=apple();x['observations']=[]
    x['document'].update(reporting_standard=None,reporting_currency=None,eps_share_basis=None)
    assert r.validate(x)['observations']==[]
    x['observations']=[apple()['observations'][0]]
    with pytest.raises(ValueError):r.validate(x)


def test_announcement_url_cannot_be_relabeled_as_a_release():
    x=next(x for x in records() if x['ticker']=='ARM')
    x['document'].update(document_type='earnings_release',release_date='2026-11-04')
    with pytest.raises(ValueError,match='publication evidence'):r.validate(x)


@pytest.mark.parametrize('metrics,expected',[(0,'published_pending'),(1,'published_partial'),(2,'published_complete')])
def test_published_completeness(metrics,expected):
    e=event();e['revenue_actual']={} if metrics else None;e['reported_eps_actual']={} if metrics==2 else None
    state=r.publication_state(e,[{'document_type':'earnings_release'}])
    assert state['code']==expected and len(state['missing_metrics'])==2-metrics


@pytest.mark.parametrize('instant,expected',[
 ('2026-11-01T20:00:00+00:00','scheduled'),('2026-11-02T23:00:00+00:00','scheduled'),
 ('2026-11-04T09:00:00+00:00','date_passed_unconfirmed')])
def test_announcement_never_means_published(instant,expected):
    state=r.publication_state(event(),[{'document_type':'earnings_date_announcement'}],datetime.fromisoformat(instant))
    assert state['code']==expected


def test_call_different_day_not_publication_clock():
    e=event();e['release'].update(precision='exact',scheduled_at_utc='2026-11-02T21:00:00+00:00')
    e['call'].update(date_status='confirmed',source_local_date='2026-11-03',scheduled_at_utc='2026-11-03T22:00:00+00:00')
    assert r.publication_state(e,[],datetime(2026,11,2,22,tzinfo=timezone.utc))['code']=='date_passed_unconfirmed'
    e['release'].update(date_status='unknown');e['call'].update(date_status='unknown',source_local_date=None)
    assert r.publication_state(e,[])['code']=='unconfirmed'


def test_same_day_arm_qualcomm_are_scheduled():
    for x in records():
        if x['ticker'] not in ('ARM','QCOM'):continue
        assert not x['observations'] and x['document']['document_type']=='earnings_date_announcement'
    e=event();e['release'].update(precision='after_close',source_local_date='2026-11-04',source_timezone='America/New_York')
    assert r.publication_state(e,[],datetime(2026,11,4,9,tzinfo=timezone.utc))['code']=='scheduled'
