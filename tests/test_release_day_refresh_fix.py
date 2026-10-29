"""R1 regression sequences: synthetic BEA headers and stored readings, offline."""
import copy
import json
from datetime import date, datetime, timezone

import httpx
import pytest

from app.analytics.calendar_readings import bind_events
from app.ingestion import sync_calendar_periods as sync
from tests.test_calendar_agenda import event, point

URL='https://www.bea.gov/news/2026/gdp-advance-estimate-3rd-quarter-2026'
PROOF=dict(release_id=53,series_ids=['GDPC1'],release_date='2026-10-29',reference_period='2026-07-01',estimate_stage='advance',binding_method='official_schedule',source_url=sync.SOURCES['bea'],report_url=URL,retrieved_at='2026-10-29T12:00:00+00:00')
NOW=datetime(2026,10,29,12,52,tzinfo=timezone.utc)


def document(header='8:30 a.m. EDT, Thursday, October 29, 2026',title='GDP (Advance Estimate), 3rd Quarter 2026'):
    return '<h1>News Release</h1><h1>'+title+'</h1><div class="field--name-field-release-date">EMBARGOED UNTIL RELEASE AT '+header+'</div>'


def test_embargo_only_confirms_advance_and_iana_instant():
    result=sync.parse_bea_result(document(),PROOF,URL,NOW.isoformat())
    assert result['announced_at']=='2026-10-29T12:30:00+00:00'
    assert result['release_time']=='08:30:00' and result['source_timezone']=='America/New_York'
    assert result['estimate_stage']=='advance' and result['reference_period']=='2026-07-01'


def test_est_header_and_older_metadata_structure_are_supported():
    proof={**PROOF,'release_date':'2026-11-25','estimate_stage':'second'}
    html=document('8:30 a.m. EST, Wednesday, November 25, 2026','GDP (Second Estimate), 3rd Quarter 2026')
    assert sync.parse_bea_result(html,proof,URL,NOW.isoformat())['announced_at']=='2026-11-25T13:30:00+00:00'
    old='<meta property="article:published_time" content="2026-10-29T08:30:00-04:00"><h1>Gross Domestic Product, 3rd Quarter 2026 (Advance Estimate)</h1>'
    assert sync.parse_bea_result(old,PROOF,URL,NOW.isoformat())['reference_period']=='2026-07-01'


@pytest.mark.parametrize('html',[
    document().replace('Thursday','Friday'),
    document().replace('October 29, 2026','October 29, 2025'),
    document().replace('3rd Quarter','2nd Quarter'),
    document().replace('Advance Estimate','Second Estimate'),
    document().replace('Advance Estimate','Third Estimate'),
    document().replace('8:30 a.m.','9:30 a.m.'),
    document().replace(' EDT,',' EST,'),
    document().replace('GDP (Advance Estimate), 3rd Quarter 2026','Personal Income and Outlays, September 2026'),
    '<h1>GDP (Advance Estimate), 3rd Quarter 2026</h1><p>October 29, 2026</p>',
    document()+'<meta property="article:published_time" content="2026-10-28T08:30:00-04:00">',
    document()+'<time datetime="2026-10-30T08:30:00-04:00"></time>',
    document()+'<meta property="article:published_time" content="2026-10-29T09:30:00-04:00">',
    document()+'<div class="release-embargo">EMBARGOED UNTIL RELEASE AT 8:30 a.m. EDT, Friday, October 30, 2026</div>',
])
def test_invalid_or_conflicting_bea_evidence_is_rejected(html):
    with pytest.raises(ValueError):sync.parse_bea_result(html,PROOF,URL,NOW.isoformat())


@pytest.mark.parametrize('url',['https://other.example/news/result','https://www.bea.gov.evil.test/news/result','https://www.bea.gov/about/result'])
def test_publisher_identity_is_checked(url):
    with pytest.raises(ValueError):sync.parse_bea_result(document(),PROOF,url,NOW.isoformat())


def test_conflict_between_legacy_metadata_and_time_element_is_not_ignored():
    html='<meta property="article:published_time" content="2026-10-29"><time datetime="2026-10-28"></time><h1>GDP (Advance Estimate), 3rd Quarter 2026</h1>'
    with pytest.raises(ValueError):sync.parse_bea_result(html,PROOF,URL,NOW.isoformat())


def test_validated_receipt_is_saved_and_later_parser_error_preserves_it(tmp_path,monkeypatch):
    from app import source_checks
    from app.analytics import fomc_calendar
    runs={}
    monkeypatch.setattr(source_checks,'write_run',lambda run:runs.__setitem__(run['id'],copy.deepcopy(run)))
    monkeypatch.setattr(fomc_calendar,'read_schedule',lambda:{'events':[]})
    reviewed=tmp_path/'reviewed.json';reviewed.write_text(json.dumps({'version':1,'periods':[]}))
    monkeypatch.setattr(sync,'REVIEWED',reviewed)
    target=tmp_path/'derived'/'periods.json';target.parent.mkdir()
    target.write_text(json.dumps({'version':1,'periods':[PROOF]}))
    html=[document()]
    def reply(request):
        assert str(request.url) in (URL,sync.SOURCES['bea'])
        return httpx.Response(200,text=html[0] if str(request.url)==URL else '<table></table>')
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        good=sync.sync_periods(client,date(2026,10,29),date(2026,10,29),[],NOW,path=target,source_kinds={'bea'})
        receipt=good['results'][0]
        assert receipt['announced_at']=='2026-10-29T12:30:00+00:00'
        assert json.loads(target.read_text())['results']==[receipt]
        html[0]=document().replace('Thursday','Friday')
        bad=sync.sync_periods(client,date(2026,10,29),date(2026,10,29),[],NOW,path=target,source_kinds={'bea'})
    assert bad['results']==[receipt]
    assert any(c['source_url']==URL and c['status']=='error' for c in bad['checks'])
    assert any(r['status']=='partial' and r['error_code']=='publisher_source_unavailable' for r in runs.values())


@pytest.mark.parametrize('signal',['elapsed','provider_success','pdf','unchanged_hash','wrong_period'])
def test_release_day_missing_gdp_does_not_borrow_pce_claims_or_provider_signals(signal):
    events=[event(53,'2026-10-29',('GDPC1',)),event(54,'2026-10-29',('PCEPI',)),event(180,'2026-10-29',('ICSA','CCSA'))]
    proof=[PROOF]
    for rid,sid,period in [(54,'PCEPI','2026-09-01'),(180,'ICSA','2026-10-24'),(180,'CCSA','2026-10-17')]:
        proof.append({**PROOF,'release_id':rid,'series_ids':[sid],'reference_period':period,'estimate_stage':None})
    evidence={'periods':proof,'results':[sync.parse_bea_result(document(),PROOF,URL,NOW.isoformat())] if signal=='pdf' else []}
    rows={'GDPC1':[point('2026-01-01',99),point('2026-04-01',100)],
          'PCEPI':[point('2026-07-01',100),point('2026-08-01',101),point('2026-09-01',102)],
          'ICSA':[point('2026-10-17',200000),point('2026-10-24',190000)],
          'CCSA':[point('2026-10-10',1700000),point('2026-10-17',1600000)]}
    if signal=='wrong_period':rows['GDPC1'].append(point('2026-10-01',103))
    updates={sid:'2026-10-29 07:34:00-05' for sid in rows}
    first=bind_events(events,{},rows,NOW,evidence,updates)
    gdp=first[0]['measures'][0]
    assert gdp['actual'] is None and gdp['previous']==pytest.approx((100/99)**4*100-100)
    assert gdp['previous_period']=='2026-04-01' and gdp['forecast'] is None
    assert gdp['missing_reason']['actual']=='observation_missing'
    assert all(m['actual'] is not None for e in first[1:] for m in e['measures'])
    # A candidate snapshot cannot change a response already in the visible generation.
    visible=copy.deepcopy(first)
    rows['GDPC1'].append(point('2026-07-01',101,'2026-10-29'))
    candidate=bind_events(events,{},rows,datetime(2026,10,29,13,9,tzinfo=timezone.utc),evidence,updates)
    assert visible[0]['measures'][0]['actual'] is None
    visible=candidate
    assert visible[0]['measures'][0]['actual']==pytest.approx((101/100)**4*100-100)
    assert visible[0]['measures'][0]['data_version']=='current_vintage'
    assert visible[0]['measures'][0]['forecast'] is None
