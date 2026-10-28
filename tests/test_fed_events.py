"""Offline Fed calendar fixtures: each timestamp has its own publisher evidence."""
import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.analytics import fomc_calendar
from app.analytics.calendar_readings import bind_events
from app.ingestion.sync_fomc_calendar import sync_schedule, monthly_events, related_meeting, parse_meetings

NOW = datetime(2026, 10, 27, 18, tzinfo=timezone.utc)


def meeting(month, days, links=''):
    return f'<div class="row fomc-meeting"><div class="fomc-meeting__month">{month}</div><div class="fomc-meeting__date">{days}</div>{links}</div>'


def schedule(document=False, december='8-9*'):
    links = '<a href="/monetarypolicy/fomcprojtabl20260916.htm">HTML</a><a href="/monetarypolicy/fomcpresconf20260916.htm">Press Conference</a><a href="/monetarypolicy/fomcminutes20260916.htm">HTML</a>(Released October 07, 2026)'
    if document:
        links += '<a href="/monetarypolicy/fomcminutes20261028.htm">HTML</a>'
    return '<div class="panel"><h4>2026 FOMC Meetings</h4>'+meeting('September','15-16*',links)+meeting('October','27-28')+meeting('December',december)+'</div><div class="panel"><h4>2027 FOMC Meetings</h4>'+meeting('January','26-27')+meeting('March','16-17*')+'</div>'


def row(title, day, clock='2:00 p.m.', detail=''):
    return f'<div class="row"><div><p>{clock}</p></div><div><p>{title}</p><p>{detail}</p></div><div>{day}</div></div>'


def pages(clock='2:30 p.m.', minutes_day=18, december_day=9):
    return {
        '2026-september.htm':'<h4>September 2026</h4>'+row('FOMC Press Conference',16,clock),
        '2026-october.htm':'<h4>October 2026</h4>'+row('FOMC Meeting',28,detail='Two-day meeting, October 27-28')+row('FOMC Press Conference',28,clock)+row('FOMC Minutes',7,detail='Meeting of September 15-16'),
        '2026-november.htm':'<h4>November 2026</h4>'+row('FOMC Minutes',minutes_day,detail='Meeting of October 27-28'),
        '2026-december.htm':'<h4>December 2026</h4>'+row('FOMC Meeting',december_day,detail='Two-day meeting, December 8-9')+row('FOMC Press Conference',december_day,clock)+row('FOMC Minutes',30,detail=f'Meeting of December 8-{december_day}'),
    }


def sync(tmp_path, html=None, content=None, failures=()):
    def respond(request):
        url = str(request.url)
        if url == fomc_calendar.SOURCE_URL:
            return httpx.Response(200,text=html or schedule())
        name = url.rsplit('/',1)[-1]
        if name in failures:
            return httpx.Response(503)
        return httpx.Response(200,text=(content or pages()).get(name,'<h4>No published calendar</h4>'))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        return sync_schedule(client,tmp_path/'derived/fed.json',tmp_path/'raw',NOW)


@pytest.fixture(autouse=True)
def isolate_checks(monkeypatch):
    from app import source_checks
    monkeypatch.setattr(source_checks,'write_run',lambda run:None)


def test_distinct_types_meetings_separate_clocks_and_no_october_sep(tmp_path):
    payload = sync(tmp_path)
    events = payload['events']
    oct_events = [e for e in events if e['release_date']=='2026-10-28']
    assert {e['event_type'] for e in oct_events} == {'fomc_decision','fomc_press_conference'}
    assert {datetime.fromisoformat(e['release_datetime_utc']).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M') for e in oct_events} == {'19:00','19:30'}
    minutes = next(e for e in events if e['event_type']=='fomc_minutes' and e['release_date']=='2026-11-18')
    assert minutes['meeting_end_date']=='2026-10-28' and minutes['release_time']=='14:00:00'
    sep = next(e for e in events if e['event_type']=='fomc_sep' and e['release_date']=='2026-12-09')
    assert sep['time_status']=='unconfirmed' and sep['release_datetime_utc'] is None
    assert sep['date_status']=='confirmed' and sep['document_url'] is None
    assert len({e['event_id'] for e in events})==len(events)
    assert not any('dot' in e['event_type'] for e in events)
    assert not any(e['event_type']=='fomc_press_conference' and e['release_date'].startswith('2027') for e in events)
    assert all(e.get('expects_numeric_result') is False and e['measures']==[] for e in events if e['event_type']!='fomc_decision')
    rebound = bind_events(events,{}, {},NOW)
    assert all(e['measures']==[] for e in rebound if e['event_type']!='fomc_decision')
    assert next(e for e in rebound if e['event_type']=='fomc_decision')['expects_numeric_result'] is True


def test_repeatable_then_changed_time_and_minutes_date_update_same_identity(tmp_path):
    first = sync(tmp_path)
    assert sync(tmp_path)==first
    updated = sync(tmp_path,content=pages('3:00 p.m.',19))
    old = next(e for e in first['events'] if e['event_type']=='fomc_minutes' and e['release_date']=='2026-11-18')
    new = next(e for e in updated['events'] if e['event_id']==old['event_id'])
    assert new['release_date']=='2026-11-19'
    assert not any(e['release_date']=='2026-11-18' for e in updated['events'])
    assert any(h['event_id']==old['event_id'] and h['before']['release_date']=='2026-11-18' for h in updated['history'])
    assert sync(tmp_path,content=pages('3:00 p.m.',19))==updated


def test_changed_meeting_date_preserves_related_identity_and_history(tmp_path):
    first = sync(tmp_path)
    changed = sync(tmp_path,html=schedule(december='8-10*'),content=pages(december_day=10))
    old = next(e for e in first['events'] if e['event_type']=='fomc_sep' and e['release_date']=='2026-12-09')
    assert next(e for e in changed['events'] if e['event_id']==old['event_id'])['release_date']=='2026-12-10'
    assert changed['history']


def test_failed_month_keeps_confirmed_schedule_and_corrupt_main_keeps_snapshot(tmp_path):
    first = sync(tmp_path)
    second = sync(tmp_path,failures=('2026-october.htm','2026-november.htm'))
    assert set(second['page_errors'])=={
        'https://www.federalreserve.gov/newsevents/2026-october.htm',
        'https://www.federalreserve.gov/newsevents/2026-november.htm'}
    original = {e['event_id']:e for e in first['events']}
    for event in second['events']:
        assert event['release_datetime_utc']==original[event['event_id']]['release_datetime_utc']
    path = tmp_path/'derived/fed.json'
    before = path.read_bytes()
    with pytest.raises(ValueError):
        sync(tmp_path,html='<h4>Invalid</h4>')
    assert path.read_bytes()==before


def test_documents_independent_from_occurrence_and_late_availability(tmp_path):
    first = sync(tmp_path)
    sept = next(e for e in first['events'] if e['event_type']=='fomc_sep' and e['release_date']=='2026-09-16')
    assert sept['document_url'].endswith('fomcprojtabl20260916.htm')
    assert sept['document_status']=='available'
    assert sept['release_time'] is None  # Document link is not publication-clock evidence.
    html = schedule().replace(meeting('October','27-28'),meeting('October','27-28','<a href="/monetarypolicy/fomcminutes20261028.htm">HTML</a>(Released November 18, 2026)'))
    second = sync(tmp_path,html=html)
    minutes = next(e for e in second['events'] if e['event_type']=='fomc_minutes' and e['meeting_end_date']=='2026-10-28')
    assert minutes['document_status']=='available'
    assert any(h['event_id']==minutes['event_id'] for h in second['history'])


@pytest.mark.parametrize('day,expected',[('2026-03-18','19:30'),('2026-10-28','19:30'),('2026-12-09','20:30')])
def test_conference_dst(day,expected):
    from app.ingestion.sync_fomc_calendar import nonnumeric_event
    d=date.fromisoformat(day)
    event=nonnumeric_event(dict(start=d,end=d,meeting_id='fixture',documents={}), 'fomc_press_conference',d,'14:30:00',NOW.isoformat(),fomc_calendar.SOURCE_URL,'hash')
    assert datetime.fromisoformat(event['release_datetime_utc']).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==expected


def test_january_minutes_link_previous_december_and_ignore_wrong_meeting():
    meetings=parse_meetings(schedule(),2026,detailed=True)
    html='<h4>January 2027</h4>'+row('FOMC Minutes',6,detail='Meeting of December 8-9, 2026')
    item=monthly_events(html,date(2027,1,1))[0]
    assert related_meeting(item,meetings)['end']==date(2026,12,9)
    item['description']='Meeting of December 11-12'
    assert related_meeting(item,meetings) is None


def test_sep_clock_requires_explicit_sep_row(tmp_path):
    content=pages()
    content['2026-december.htm']+=row('Summary of Economic Projections',9,'2:15 p.m.')
    events=sync(tmp_path,content=content)['events']
    sep=next(e for e in events if e['event_type']=='fomc_sep' and e['release_date']=='2026-12-09')
    assert sep['release_time']=='14:15:00' and sep['time_source_url'].endswith('2026-december.htm')


def test_policy_outlook_still_selects_decisions_only(tmp_path,monkeypatch):
    payload=sync(tmp_path)
    monkeypatch.setattr(fomc_calendar,'read_schedule',lambda:{'status':'available',**payload})
    assert fomc_calendar.policy_outlook(datetime(2026,10,28,18,15,tzinfo=timezone.utc))['next_decision']['release_date']=='2026-12-09'


def test_real_fastapi_route_serializes_related_events_and_category(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.analytics import release_calendar
    from tests.test_release_calendar import FakeConnection
    payload=sync(tmp_path)
    monkeypatch.setattr(release_calendar,'read_schedule',lambda:{'status':'available',**payload})
    monkeypatch.setattr(release_calendar,'get_connection',lambda:FakeConnection([[]]))
    with TestClient(app) as client:
        response=client.get('/api/v1/calendar?start_date=2026-12-09&end_date=2026-12-09&category=financial_conditions')
        assert response.status_code==200
        events=response.json()['events']
        assert {e['event_type'] for e in events}=={'fomc_decision','fomc_press_conference','fomc_sep'}
        assert all(e['release_id'] is None for e in events)
        sep=next(e for e in events if e['event_type']=='fomc_sep')
        assert sep['release_datetime_utc'] is None and sep['expects_numeric_result'] is False
        assert sep['measures']==[] and sep['meeting_end_date']=='2026-12-09'
        assert client.get('/api/v1/calendar?start_date=2026-12-09&end_date=2026-12-09&category=inflation').json()['events']==[]
