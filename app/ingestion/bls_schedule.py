"""BLS formats and source cache for the existing calendar evidence snapshot.

The coordinator owns locking and publication. This adapter never schedules jobs,
fetches indicator values, or treats a schedule as result availability.
"""
import copy
import os
import re
import time
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import httpx

from app.ingestion.request_budget import before_request
from app.ingestion.sync_fomc_calendar import Tree

# Public links verified in https://www.bls.gov/schedule/ (By News Release).
GROUPS = {
    'Employment Situation': (50, ['PAYEMS', 'UNRATE', 'CES0500000003'], 'empsit'),
    'Consumer Price Index': (10, ['CPIAUCSL', 'CPILFESL'], 'cpi'),
    'Producer Price Index': (46, ['PPIFIS'], 'ppi'),
    'Employment Cost Index': (11, ['ECIALLCIV'], 'eci'),
    'Job Openings and Labor Turnover Survey': (192, ['JTSJOL'], 'jolts'),
}
PRIORITY = {'bls_release_table': 3, 'bls_monthly_list': 2,
            'official_calendar_feed': 1}


def identity(row):
    return row['release_id'], row['reference_period']


def publisher_identity(row):
    """A GDP estimate, M3 full report or permits revision is its own release."""
    return row['release_id'], row['reference_period'], row.get('estimate_stage') or ''


def signature(row):
    return row['release_date'], row.get('release_time')


def parse_html(html, url, retrieved, publication=None):
    """Strict explicit table/list rows; never infer a reference month."""
    from app.ingestion.sync_calendar_periods import cells, parsed_date
    tree = Tree(html)
    records = []
    for table in tree.root.find(lambda n: n.tag == 'table'):
        headers = ' '.join(n.text() for n in table.find(lambda n: n.tag == 'th'))
        primary = publication is not None and 'Reference Month' in headers and 'Release Date' in headers and 'Release Time' in headers
        for row in table.find(lambda n: n.tag == 'tr'):
            c = cells(row)
            if primary and c and len(c)!=3 and row.find(lambda n:n.tag=='td'):
                raise ValueError('Incomplete BLS release table row')
            if not primary and len(c)!=3 and row.find(lambda n:n.tag=='td') and any(name in row.text() for name in GROUPS):
                raise ValueError('Incomplete BLS monthly list row')
            if len(c) != 3 or row.find(lambda n: n.tag == 'th'):
                continue
            if primary:
                name, period, day, clock = publication, c[0], c[1], c[2]
            else:
                match = next(((name, re.fullmatch(re.escape(name) + r' for (.+)', c[2]))
                              for name in GROUPS if c[2]==name or c[2].startswith(name + ' for')), None)
                if not match:
                    continue
                name, matched = match
                if not matched:
                    raise ValueError('Incomplete BLS list row')
                period, day, clock = matched[1], c[0], c[1]
            # A recognized but malformed row invalidates this response. Do not
            # turn a partial parse into a successful replacement of old content.
            ref, released = parsed_date(period), parsed_date(day)
            clock = datetime.strptime(clock.strip(), '%I:%M %p').time().isoformat()
            if (name == 'Employment Cost Index' and not re.search(r'Quarter', period, re.I)):
                raise ValueError('ECI requires an explicit quarter')
            if name != 'Employment Cost Index' and not re.fullmatch(r'[A-Za-z]+ \d{4}', period.strip()):
                raise ValueError('BLS monthly reference is ambiguous')
            rid, sids, _ = GROUPS[name]
            records.append(dict(release_id=rid, series_ids=sids, release_date=released,
                reference_period=ref, release_time=clock, source_timezone='America/New_York',
                source_url=url, retrieved_at=retrieved, estimate_stage=None,
                binding_method='bls_release_table' if primary else 'bls_monthly_list'))
    if not records:
        raise ValueError('No explicit supported BLS schedule rows')
    seen = {}
    for row in records:
        key = identity(row)
        if key in seen and signature(seen[key]) != signature(row):
            raise ValueError('Conflicting rows within BLS response')
        seen[key] = row
    return list(seen.values())


def select_records(rows, group_ids=None, priority=None, identity_key=identity):
    """Deterministic published-source precedence, with unresolved peers withheld."""
    groups = {}
    group_ids=group_ids if group_ids is not None else {g[0] for g in GROUPS.values()}
    priority=priority if priority is not None else PRIORITY
    for row in rows:
        if row['release_id'] in group_ids:
            groups.setdefault(identity_key(row), []).append(row)
    selected, conflicts = [], []
    for key, candidates in sorted(groups.items()):
        rank = max(priority.get(r.get('binding_method'), 0) for r in candidates)
        peers = [r for r in candidates if priority.get(r.get('binding_method'), 0) == rank]
        # A missing clock is not a disagreement with a known clock.
        dates = {r['release_date'] for r in peers}
        clocks = {r['release_time'] for r in peers if r.get('release_time')}
        unresolved = len(dates) > 1 or len(clocks) > 1
        if len({r['release_date'] for r in candidates}) > 1 or len({r['release_time'] for r in candidates if r.get('release_time')}) > 1:
            conflicts.append(dict(release_id=key[0], reference_period=key[1],
                resolution='unresolved' if unresolved else 'documented_source_priority',
                candidates=copy.deepcopy(candidates)))
        if not unresolved:
            selected.append(max(peers, key=lambda r: (bool(r.get('release_time')), r['retrieved_at'], r['source_url'])))
    # Different reference periods on the same release date are also ambiguous.
    day_groups = {}
    for row in selected:
        day_groups.setdefault((row['release_id'], row['release_date']), []).append(row)
    for key, peers in day_groups.items():
        if len(peers) > 1:
            conflicts.append(dict(release_id=key[0], release_date=key[1], resolution='unresolved', candidates=peers))
    return [r for r in selected if len(day_groups[(r['release_id'], r['release_date'])]) == 1], conflicts


def merge_source(data, url, rows, identity_key=identity):
    """Upsert only explicit identities; absent rows never imply cancellation."""
    old = data['periods']
    history = data.setdefault('bls_history', [])
    for row in rows:
        matches = [r for r in old if r['source_url'] == url and identity_key(r) == identity_key(row)]
        unchanged = next((r for r in matches if signature(r) == signature(row)
                          and r.get('series_ids') == row['series_ids']
                          and (not row.get('raw_hash') or r.get('raw_hash') == row['raw_hash'])), None)
        if unchanged:
            continue  # Original content acquisition date is stable on revalidation.
        for prior in matches:
            if prior not in history:
                history.append(prior)
            old.remove(prior)
        old.append(row)


def interval_seconds():
    return max(900, int(os.getenv('BLS_SCHEDULE_MIN_INTERVAL_SECONDS', '86400')))


def sources_due(evidence, now):
    states = {r['source_url']: r for r in evidence.get('bls_sources', [])}
    return any(not states.get(f'https://www.bls.gov/schedule/news_release/{g[2]}.htm', {}).get('attempted_at')
               or now >= datetime.fromisoformat(states[f'https://www.bls.gov/schedule/news_release/{g[2]}.htm']['attempted_at']) + timedelta(seconds=interval_seconds())
               for g in GROUPS.values())


def sync_sources(client, data, start, end, now, raw):
    """Called inside sync_periods under the existing job lock/request budget."""
    from app.ingestion.sync_calendar_periods import parse_bls_ics
    stamp = now.isoformat()
    states = {r['source_url']: copy.deepcopy(r) for r in data.get('bls_sources', [])}
    checks = []

    def source(url, publication=None, ics=False):
        state = states.setdefault(url, {'source_url': url})
        attempted = state.get('attempted_at')
        if attempted and now < datetime.fromisoformat(attempted) + timedelta(seconds=interval_seconds()):
            checks.append(dict(source_url=url, status=state.get('status', 'error'), cached=True,
                checked_at=state.get('last_successful_check'), error_code=state.get('error_code')))
            return state.get('status') == 'success'
        state['attempted_at'] = stamp
        headers = {}
        if state.get('etag'): headers['If-None-Match'] = state['etag']
        if state.get('last_modified'): headers['If-Modified-Since'] = state['last_modified']
        try:
            for attempt in range(2):
                before_request('publisher')
                try:
                    response = client.get(url, headers=headers)
                    if response.status_code in (500, 502, 503, 504) and attempt == 0:
                        time.sleep(1)
                        continue
                    if response.status_code != 304:
                        response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt: raise
                    time.sleep(1)
            if urlparse(str(response.url)).hostname != 'www.bls.gov':
                raise ValueError('Unexpected BLS redirect host')
            if response.status_code == 304:
                if not state.get('content_retrieved_at'):
                    raise ValueError('304 without a validated cached representation')
            else:
                content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
                if content_type not in ('text/html', 'text/calendar', 'text/plain', 'application/octet-stream'):
                    raise ValueError('Unexpected BLS Content-Type')
                text = response.text
                if re.search(r'<(?:title|h[12])[^>]*>\s*(?:Access Denied|Error|Service Unavailable)', text, re.I):
                    raise ValueError('BLS error page returned with HTTP 200')
                rows = parse_bls_ics(text, url, stamp) if ics else parse_html(text, url, stamp, publication)
                merge_source(data, url, rows)
                capture = raw / (f'bls-{len(list(raw.iterdir()))}' + ('.ics' if ics else '.html'))
                capture.write_bytes(response.content)
                state.update(content_retrieved_at=stamp, capture=str(capture),
                    etag=response.headers.get('ETag'), last_modified=response.headers.get('Last-Modified'),
                    coverage={'release_from': min(r['release_date'] for r in rows), 'release_through': max(r['release_date'] for r in rows),
                              'reference_from': min(r['reference_period'] for r in rows), 'reference_through': max(r['reference_period'] for r in rows), 'records': len(rows)})
            state.update(status='success', last_successful_check=stamp, error_code=None)
            checks.append(dict(source_url=url, status='success', checked_at=stamp,
                http_status=response.status_code, retrieved_at=state['content_retrieved_at'], coverage=state.get('coverage')))
            return True
        except Exception as error:
            state.update(status='error', error_code=type(error).__name__)
            checks.append(dict(source_url=url, status='error', attempted_at=stamp,
                http_status=error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None,
                error_code=type(error).__name__, last_successful_check=state.get('last_successful_check')))
            return False

    primary_ok = [source(f'https://www.bls.gov/schedule/news_release/{code}.htm', name)
                  for name, (_, _, code) in GROUPS.items()]
    if not all(primary_ok):
        # Lists cover the requested window only. Their shorter coverage never
        # replaces the longer per-publication table or old saved rows.
        month = date(start.year, start.month, 1)
        while month <= end:
            source(f'https://www.bls.gov/schedule/{month.year}/{month.month:02d}_sched_list.htm')
            month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
        source('https://www.bls.gov/schedule/news_release/bls.ics', ics=True)
    data['bls_sources'] = list(states.values())
    return checks
