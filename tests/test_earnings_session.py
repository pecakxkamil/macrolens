import copy
import pytest
from app import earnings_session as s


@pytest.mark.parametrize('day,close', [('2026-03-16','20:00'),('2026-10-29','20:00'),
                                     ('2026-11-02','21:00'),('2026-11-27','18:00'),('2026-12-24','18:00')])
def test_reviewed_sessions_use_new_york_dst_and_real_early_closes(day, close):
    assert s.session(day)['close_at_utc'][11:16] == close
    assert s.session(day)['source'] == s.SOURCE


@pytest.mark.parametrize('day', [None,'invalid','2026-11-28','2026-11-26','2026-07-03','2027-11-02'])
def test_no_invented_session_on_holiday_weekend_or_unreviewed_year(day):
    assert s.session(day) is None


def test_context_is_additive_uses_reviewed_identity_and_does_not_touch_evidence():
    events=[dict(cik='0000320193',ticker='AAPL',release=dict(source_local_date='2026-11-02',precision='date_only'),
                 call=dict(scheduled_at_utc='2026-11-02T22:00:00+00:00'),current_eps_actual='unchanged')]
    before=copy.deepcopy(events)
    s.attach(events)
    context=events[0].pop('session_context')
    assert context['us_listed'] and context['release']['date']==context['call']['date']=='2026-11-02'
    assert events==before
    events[0]['ticker']='WRONG'
    assert not s.attach(events)[0]['session_context']['us_listed']


def test_new_york_session_day_comes_from_absolute_instant_not_publisher_timezone():
    events=[dict(cik='0000320193',ticker='AAPL',
                 release=dict(source_local_date='2026-11-02',scheduled_at_utc='2026-11-03T05:30:00+00:00'),
                 call={})]
    context=s.attach(events)[0]['session_context']
    assert context['release']['date']=='2026-11-03' and context['call'] is None
