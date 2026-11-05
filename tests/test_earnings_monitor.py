import copy
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import httpx
import pytest
from app import earnings_monitor_policy as p, earnings_monitor_sources as s
from app import earnings_monitor as m
from app.database import activate_earnings_monitor as activation


def event(day='2026-11-04', precision='after_close'):
    return dict(ticker='QCOM',cik='0000804328',fiscal_year=2026,fiscal_quarter=4,period_label='Q4 FY2026',
                release=dict(date_status='confirmed',precision=precision,source_local_date=day),
                call=dict(date_status='unknown'),publication_state=dict(code='scheduled'))


@pytest.mark.parametrize('day,clock',[('2026-11-04','21:00'),('2026-10-29','20:00'),('2026-03-16','20:00'),('2026-11-27','18:00')])
def test_fifteen_minute_slots_use_actual_session_close(day,clock):
    e=event(day);plan=p.schedule(e)
    assert plan['slots'][0]==p.instant(day+'T'+clock+':00Z')
    assert [t-plan['start'] for t in plan['slots'][:25]]==[timedelta(minutes=15*i) for i in range(25)]
    assert plan['end']-plan['start']==timedelta(hours=48)


def test_no_call_time_start_and_restart_coalesces_missed_slots():
    e=event();e['call']['scheduled_at_utc']='2026-11-04T22:00:00Z'
    now=p.instant('2026-11-04T21:34:00Z');due=p.due(e,now,[])
    assert due['slot']==p.instant('2026-11-04T21:30:00Z')
    rows=[dict(phase='started',scheduled_for=due['slot'],status='started')]
    assert p.due(e,now,rows) is None
    assert p.due(e,now+timedelta(minutes=15),rows)['slot']==p.instant('2026-11-04T21:45:00Z')
    assert p.due(e,p.instant('2026-11-04T20:59:59Z'),[]) is None


@pytest.mark.parametrize('day',['2026-11-26','2026-11-28','2027-11-04'])
def test_no_holiday_weekend_or_unreviewed_year_session(day):
    assert p.schedule(event(day)) is None


def test_before_open_unknown_slow_schedule_and_expiry():
    before=p.schedule(event(precision='before_open'))
    assert before['start']==p.instant('2026-11-04T08:30:00Z')
    unknown=p.schedule(event(precision='date_only'))
    assert unknown['slots'][1]-unknown['slots'][0]==timedelta(hours=2)
    assert p.due(event(),p.instant('2026-11-07T00:00:00Z'),[])['expired']
    e=event();e['publication_state']['code']='published_complete'
    assert p.schedule(e) is None


def test_complete_blocked_reviewed_and_backoff_stop_requests():
    now=p.instant('2026-11-04T22:00:00Z')
    for status in ('imported','review_required','blocked'):
        assert p.due(event(),now,[dict(phase='result',status=status)]) is None
    assert p.due(event(),now,[dict(phase='result',status='http_retry',retry_after=now+timedelta(minutes=15))]) is None


@pytest.mark.parametrize('status,kind',[(404,s.NotPublished),(403,s.ReviewRequired),(429,s.RetryHTTP),(500,s.RetryHTTP),(503,s.RetryHTTP)])
def test_http_failure_never_becomes_a_report(tmp_path,status,kind):
    spec=s.bindings()[1]
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(status,headers={'retry-after':'1800'}))) as client:
        with pytest.raises(kind):s.fetch(client,spec,tmp_path,p.instant('2026-11-04T21:00:00Z'))


def test_unreviewed_redirect_and_publisher_challenge_stop(tmp_path):
    spec=s.bindings()[1]
    for response in (httpx.Response(302,headers={'location':'https://unreviewed.invalid/report'}),httpx.Response(200,content=b'<html>captcha</html>')):
        with httpx.Client(transport=httpx.MockTransport(lambda request:response)) as client:
            with pytest.raises(s.ReviewRequired):s.fetch(client,spec,tmp_path,p.instant('2026-11-04T21:00:00Z'))


QCOM='Qualcomm Announces Fourth Quarter and Fiscal 2026 Results Qualcomm Incorporated (NASDAQ: QCOM) November 4, 2026 fiscal fourth quarter and year ended September 27, 2026. Fourth Quarter Results1 GAAP Non-GAAP (in millions, except per share data and percentages) Q4 Fiscal 2026 Q4 Fiscal 2025 Change Q4 Fiscal 2026 Q4 Fiscal 2025 Change Revenues $10,322 $11,270 (8%) $10,442 $11,270 (7%) Diluted earnings (loss) per share (EPS) $1.17 ($2.89) +140% $2.17 $3.00 (28%) Fiscal 2026 Results1,2'


def parse_text(text):
    body=b'%PDF synthetic';spec=s.bindings()[1]
    receipt=dict(url=spec['url'],sha256=hashlib.sha256(body).hexdigest(),fetched_at='2026-11-04T21:30:00+00:00')
    pdf=Mock(is_encrypted=False,pages=[Mock(extract_text=lambda:text)])
    with patch.object(s,'PdfReader',return_value=pdf):return s.parse(body,spec,receipt)


def test_quarterly_gaap_not_adjusted_or_annual_values():
    record=parse_text(QCOM)
    assert [v['source_value'] for v in record['observations']]==['10322','1.17']
    assert record['document']['verification_method']==s.METHOD


@pytest.mark.parametrize('old,new,kind',[
    ('Fiscal 2026','Fiscal 2025',s.NotPublished),
    ('September 27, 2026','June 28, 2026',s.NotPublished),
    ('Qualcomm Incorporated (NASDAQ: QCOM)','Another Issuer',s.ReviewRequired),
    ('GAAP Non-GAAP','Non-GAAP GAAP',s.ReviewRequired),
    ('in millions','in billions',s.ReviewRequired),
    ('Diluted earnings','Basic earnings',s.ReviewRequired)])
def test_ambiguous_identity_period_standard_scale_or_eps_never_imports(old,new,kind):
    with pytest.raises(kind):parse_text(QCOM.replace(old,new))


def test_activation_needs_a_new_explicit_hash_and_does_not_touch_db():
    c=Mock()
    with pytest.raises(ValueError,match='Separate full'):activation.apply(c,{'target_label':'local'},'local','old-e2e-hash',{})
    assert not c.mock_calls


def test_no_runtime_token_is_safe_and_does_not_connect(monkeypatch,tmp_path):
    monkeypatch.setattr(m,'TOKEN',tmp_path/'absent.json');factory=Mock()
    assert m.run(factory)==dict(status='awaiting_activation',checked=0)
    factory.assert_not_called()
