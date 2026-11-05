"""Read-only presentation context, never release evidence or an importer.

Bounded 2026 NYSE/Nasdaq cash-equity calendar reviewed 2026-11-04:
https://www.nyse.com/trade/hours-calendars
https://nasdaqtrader.com/Trader.aspx?id=Calendar
Outside this reviewed year we supply no inferred session.
"""
import json
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE = 'https://www.nyse.com/trade/hours-calendars'
HOLIDAYS = frozenset(('2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03',
                      '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
                      '2026-11-26', '2026-12-25'))
EARLY_CLOSE = frozenset(('2026-11-27', '2026-12-24'))


def session(day):
    try:
        parsed = date.fromisoformat(day)
    except (TypeError, ValueError):
        return None
    if parsed.year != 2026 or parsed.weekday() >= 5 or day in HOLIDAYS:
        return None
    def instant(hour, minute=0):
        return datetime.combine(parsed, time(hour, minute), ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()
    return dict(date=day, open_at_utc=instant(9, 30),
                close_at_utc=instant(13 if day in EARLY_CLOSE else 16), source=SOURCE)


@lru_cache(maxsize=1)
def registry():
    path = Path(__file__).resolve().parents[1] / 'config/earnings_companies_reviewed.json'
    return {r['cik']: r for r in json.loads(path.read_text(encoding='utf-8'))}


def attach(events):
    """Add calendar/listing context without changing any existing event field."""
    for event in events:
        issuer = registry().get(event['cik'], {})
        us_listed = (issuer.get('identity_status') == 'reviewed_sec'
                     and issuer.get('exchange') in ('Nasdaq', 'NYSE')
                     and event['ticker'] in (issuer.get('ticker'), *issuer.get('aliases', [])))
        release, call = event['release'], event['call']
        release_day = release.get('source_local_date') or event.get('financial_release_date') or call.get('source_local_date')
        release_instant = release.get('scheduled_at_utc') or release.get('expected_time_utc')
        if release_instant:
            release_day = datetime.fromisoformat(release_instant).astimezone(ZoneInfo('America/New_York')).date().isoformat()
        call_day = None
        if call.get('scheduled_at_utc'):
            call_day = datetime.fromisoformat(call['scheduled_at_utc']).astimezone(ZoneInfo('America/New_York')).date().isoformat()
        event['session_context'] = dict(us_listed=us_listed,
                                        release=session(release_day), call=session(call_day))
    return events
