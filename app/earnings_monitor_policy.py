"""Pure, bounded publisher-check slots. Never start from the call clock."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.earnings_session import session

UTC = timezone.utc
NY = ZoneInfo('America/New_York')


def instant(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(UTC)


def window(event):
    release, call = event['release'], event['call']
    if release['date_status'] == 'cancelled':
        return None
    if release['date_status'] in ('confirmed', 'changed'):
        if release['precision'] in ('after_close', 'before_open'):
            return release['precision']
    context = event.get('session_context') or {}
    current = context.get('release')
    at = release.get('scheduled_at_utc') or release.get('expected_time_utc')
    if current and at:
        if instant(at) < instant(current['open_at_utc']):
            return 'before_open'
        if instant(at) >= instant(current['close_at_utc']):
            return 'after_close'
        return 'unknown'
    if (release['precision'] in ('unknown', 'date_only') and context.get('us_listed')
        and current and context.get('call') and current['date'] == context['call']['date']
        and (not event.get('financial_release_date') or event['financial_release_date'] == current['date'])
        and call['date_status'] in ('confirmed', 'changed') and call.get('verified_on')
        and call.get('verification_method') == 'manually_verified_official_source'
        and call['precision'] == 'exact' and call.get('scheduled_at_utc')
        and instant(call['scheduled_at_utc']) >= instant(current['close_at_utc'])):
        return 'after_close'
    return 'unknown'


def schedule(event):
    if event.get('publication_state', {}).get('code') == 'published_complete':
        return None
    release = event['release']
    if release['date_status'] == 'cancelled':
        return None
    day = release.get('source_local_date') or event.get('financial_release_date')
    if not day or release['date_status'] not in ('confirmed', 'changed') and not event.get('financial_release_date'):
        # A call-only date is not a verified release date for an unknown window.
        if window(event) != 'after_close':
            return None
        day = event['call'].get('source_local_date')
    kind = window(event)
    market = session(day)
    if kind in ('after_close', 'before_open'):
        if not market:
            return None  # Holiday/weekend/unreviewed year: do not invent a session.
        start = instant(market['close_at_utc']) if kind == 'after_close' else instant(market['open_at_utc']) - timedelta(hours=6)
        slots = [start + timedelta(minutes=15*i) for i in range(25)]
        if kind == 'after_close':
            next_day = start.astimezone(NY).date() + timedelta(days=1)
            slow = datetime.combine(next_day, datetime.min.time(), NY).astimezone(UTC)
            slow = max(slow, slots[-1] + timedelta(hours=2))
        else:
            slow = slots[-1] + timedelta(hours=2)
    else:
        start = datetime.fromisoformat(day).replace(tzinfo=NY).astimezone(UTC)
        slots = []
        slow = start
    end = start + timedelta(hours=48)
    while slow <= end:
        slots.append(slow)
        slow += timedelta(hours=2)
    return dict(window=kind, start=start, end=end, slots=slots)


def due(event, now, attempts):
    policy = schedule(event)
    if policy is None or now < policy['start']:
        return None
    results = [r for r in attempts if r['phase'] == 'result']
    if any(r['status'] in ('imported', 'review_required', 'blocked') for r in results):
        return None
    if any(r.get('retry_after') and instant(r['retry_after']) > now for r in results):
        return None
    slot = policy['end'] if now >= policy['end'] else max(s for s in policy['slots'] if s <= now)
    if any(instant(r['scheduled_for']) == slot for r in attempts):
        return None
    return dict(slot=slot, expired=now >= policy['end'], **policy)
