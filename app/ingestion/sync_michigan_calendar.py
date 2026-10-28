"""Michigan schedule metadata only. No result downloads or numerical importer."""
import calendar
import copy
import hashlib
from io import BytesIO
import json
from datetime import date, datetime, timezone
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse, parse_qs
from uuid import uuid4

from pypdf import PdfReader
from app.ingestion.sync_fomc_calendar import Tree
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check

ROOT = Path(__file__).resolve().parents[2]
REVIEWED = ROOT / 'config/michigan_calendar_evidence.json'
SNAPSHOT = ROOT / 'data/derived/michigan_calendar_v1.json'
INFO = 'https://data.sca.isr.umich.edu/survey-info.php'
HOME = 'https://www.sca.isr.umich.edu/'
REPORTS = 'https://data.sca.isr.umich.edu/reports.php?year='
AGREEMENT = 'https://data.sca.isr.umich.edu/agreement.php'
ADAPTER_VERSION = 1
MONTHS = {name: i for i, name in enumerate(calendar.month_name) if name}


def identity(period, stage):
    return f'michigan:{period[:7]}:{stage}'


def read_schedule(path=None):
    rows, history, check = {}, [], None
    for source in ([Path(path)] if path else [REVIEWED, SNAPSHOT]):
        try:
            d = json.loads(source.read_text(encoding='utf-8'))
            if d['version'] != 1:
                continue
            validated = {}
            for row in d.get('events', []):
                if row['stage'] not in ('preliminary', 'final') or row['event_id'] != identity(row['reference_period'], row['stage']):
                    raise ValueError('Invalid Michigan identity')
                date.fromisoformat(row['release_date'])
                date.fromisoformat(row['reference_period'])
                validated[row['event_id']] = row
            rows.update(validated)
            history.extend(d.get('history', []))
            check = d.get('check') or check
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return dict(version=1, events=sorted(rows.values(), key=lambda r: r['event_id']), history=history, check=check)


def schedule_links(html):
    result = {}
    for a in Tree(html).root.find(lambda n: n.tag == 'a'):
        m = re.fullmatch(r'(20\d{2}) Release Dates', a.text().strip())
        url = urljoin(INFO, a.attrs.get('href', ''))
        if m:
            if not document_link(url) or int(m[1]) in result:
                raise ValueError('Conflicting or untrusted Michigan schedule link')
            result[int(m[1])] = url
    if not result:
        raise ValueError('Michigan release schedules not found')
    return result


def document_link(url):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname == 'data.sca.isr.umich.edu' and p.path == '/fetchdoc.php' and bool(re.fullmatch(r'\d+', parse_qs(p.query).get('docid', [''])[0]))


def parse_schedule(content, year, provenance):
    if not content.startswith(b'%PDF'):
        raise ValueError('Expected Michigan PDF schedule')
    text = ' '.join(p.extract_text() or '' for p in PdfReader(BytesIO(content)).pages)
    if not re.search(rf'RELEASE\s+DATES\s+FOR\s+{year}\s*:', text) or 'UNIVERSITY OF MICHIGAN' not in text:
        raise ValueError('Michigan calendar year or publisher not confirmed')
    months = '|'.join(MONTHS)
    pattern = rf'({months})\s+(\d{{1,2}})\s*\*?\s+({months})\s+(Prelim|Final)\b'
    rows = []
    for month, day, reference, stage in re.findall(pattern, text):
        period = str(date(year, MONTHS[reference], 1))
        kind = 'preliminary' if stage == 'Prelim' else 'final'
        rows.append(dict(event_id=identity(period, kind), stage=kind, reference_period=period,
            release_date=str(date(year, MONTHS[month], int(day))), schedule_date=str(date(year, MONTHS[month], int(day))), release_time=None,
            source_timezone='America/New_York', date_status='confirmed', time_status='unconfirmed',
            schedule_status='confirmed', schedule_provenance=copy.deepcopy(provenance),
            time_source_url=None, document_url=None, document_status='unconfirmed'))
    if len(rows) != 24 or len({r['event_id'] for r in rows}) != 24:
        raise ValueError('Incomplete or conflicting Michigan annual calendar')
    return rows


def report_links(html, year):
    result = {}
    tree = Tree(html).root
    for div in tree.find(lambda n: n.tag == 'div'):
        dates = [n.text().strip() for n in div.children if getattr(n, 'tag', '') == 'span' and n.attrs.get('class') == 'date']
        if len(dates) != 1:
            continue
        m = re.fullmatch(r'([A-Za-z]+) (20\d{2})', dates[0])
        if not m or m[1] not in MONTHS or int(m[2]) != year:
            continue
        for a in div.find(lambda n: n.tag == 'a'):
            label = re.fullmatch(r'([A-Za-z]+) (Preliminary|Final) Results', a.text().strip())
            url = urljoin(REPORTS + str(year), a.attrs.get('href', ''))
            if label and label[1] == m[1] and document_link(url):
                key = identity(str(date(year, MONTHS[m[1]], 1)), label[2].lower())
                if key in result and result[key] != url:
                    raise ValueError('Conflicting Michigan report links')
                result[key] = url
    if f'{year} Reports' not in tree.text():
        raise ValueError('Michigan reports page year not confirmed')
    return result


def home_metadata(html):
    # Read only the release announcement and summary heading. Never parse tables.
    text = Tree(html).root.text()
    month = '|'.join(MONTHS)
    upcoming = re.search(rf'Next data release:\s*[A-Za-z]+,\s*({month})\s+(\d{{1,2}}),\s*(20\d{{2}})\s+for\s+(Preliminary|Final)\s+({month})\s+data at\s+(\d{{1,2}})(?::(\d{{2}}))?\s*(am|pm)\s+ET\b', text)
    next_event = None
    if upcoming:
        a, day, year, stage, ref, hour, minute, ampm = upcoming.groups()
        h = int(hour)
        if not 1 <= h <= 12 or int(minute or 0) > 59:
            raise ValueError('Invalid publisher clock')
        h = h % 12 + (12 if ampm == 'pm' else 0)
        next_event = dict(event_id=identity(str(date(int(year), MONTHS[ref], 1)), stage.lower()),
            release_date=str(date(int(year), MONTHS[a], int(day))), release_time=f'{h:02}:{int(minute or 0):02}:00')
    current = re.search(rf'\b(Preliminary|Final) Results for ({month}) (20\d{{2}})\b', text)
    current_id = identity(str(date(int(current[3]), MONTHS[current[2]], 1)), current[1].lower()) if current else None
    if not next_event and not current_id:
        raise ValueError('Michigan release announcement not found')
    return next_event, current_id


def write_snapshot(payload, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    temp.replace(path)


def sync_schedule(client, now=None, path=None, raw_root=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    prior = read_schedule(path)
    rows = {r['event_id']: copy.deepcopy(r) for r in prior['events']}
    before = copy.deepcopy(rows)
    errors, captures, years = [], [], []
    raw_root = Path(raw_root or ROOT/'data/raw/michigan/calendar')
    raw_root.mkdir(parents=True, exist_ok=True)

    def fetch(url, retain=True):
        before_request('Michigan')
        response = client.get(url)
        if urlparse(str(response.url)).hostname not in ('www.sca.isr.umich.edu', 'data.sca.isr.umich.edu'):
            raise ValueError('Unexpected Michigan redirect')
        digest = hashlib.sha256(response.content).hexdigest()
        proof = dict(source_url=url, retrieved_at=stamp, raw_hash=digest,
                     retrieval_method='backend_http', response_body_retained=retain,
                     http_status=response.status_code)
        if retain:
            capture = raw_root/(uuid4().hex + ('.pdf' if response.content.startswith(b'%PDF') else '.html'))
            capture.write_bytes(response.content)
            proof['capture_path'] = str(capture.relative_to(ROOT)) if ROOT in capture.parents else str(capture)
        captures.append(proof)
        response.raise_for_status()
        return response, proof

    with availability_check('michigan:calendar', {'provider':'University of Michigan', 'scope':'schedule and document-link metadata only; no results'}) as check:
        try:
            response, _ = fetch(INFO)
            links = schedule_links(response.text)
        except Exception as error:
            links = {}
            errors.append(dict(source_url=INFO, error_code=type(error).__name__))
        # Only explicitly linked published schedules. Never synthesize a year.
        for year, url in links.items():
            try:
                response, proof = fetch(url)
                parsed = parse_schedule(response.content, year, proof)
                years.append(year)
                for row in parsed:
                    old = rows.get(row['event_id'])
                    if old:
                        # An unchanged annual table must not roll back a newer,
                        # explicitly dated announcement when the home fetch fails.
                        if old.get('schedule_date') == row['schedule_date']:
                            row['release_date'] = old['release_date']
                        row['schedule_status'] = old.get('schedule_status','confirmed')
                        for field in ('release_time','time_status','time_source_url','time_provenance','document_url','document_status','document_kind','document_provenance','date_source_url','date_provenance'):
                            if old.get(field) is not None:
                                row[field] = old[field]
                        # A moved annual date invalidates an old date-specific clock.
                        if row['release_date'] != old['release_date']:
                            row.update(release_time=None, time_status='unconfirmed', time_source_url=None, time_provenance=None)
                            row.pop('date_source_url',None)
                            row.pop('date_provenance',None)
                    rows[row['event_id']] = row
            except Exception as error:
                errors.append(dict(source_url=url, error_code=type(error).__name__))
        # Archive listings expose document identity only. Do not download reports.
        for year in sorted({r['reference_period'][:4] for r in rows.values() if int(r['reference_period'][:4]) <= now.year and int(r['reference_period'][:4]) >= now.year-1}):
            url = REPORTS + year
            try:
                response, proof = fetch(url)
                for key, link in report_links(response.text, int(year)).items():
                    if key in rows and rows[key]['release_date'] <= str(now.date()):
                        rows[key].update(document_url=link, document_status='available', document_kind='archive_report_link', document_provenance=proof)
            except Exception as error:
                errors.append(dict(source_url=url, error_code=type(error).__name__))
        try:
            # The home page contains numerical results: parse metadata transiently,
            # retain its response hash, but do not store its body or any numbers.
            response, proof = fetch(HOME, retain=False)
            upcoming, current = home_metadata(response.text)
            for key, row in rows.items():
                if row.get('document_kind') == 'current_summary_link' and key != current:
                    row.update(document_url=None, document_status='unconfirmed', document_kind=None, document_provenance=None)
            if upcoming and upcoming['event_id'] in rows:
                row = rows[upcoming['event_id']]
                if row['release_date'] != upcoming['release_date']:
                    row.update(date_source_url=HOME, date_provenance=proof)
                row.update(release_date=upcoming['release_date'], release_time=upcoming['release_time'],
                    time_status='confirmed', time_source_url=HOME, time_provenance=proof)
            if current in rows and rows[current]['release_date'] <= str(now.date()) and rows[current].get('document_kind') != 'archive_report_link':
                rows[current].update(document_url=HOME, document_status='available', document_kind='current_summary_link', document_provenance=proof)
        except Exception as error:
            errors.append(dict(source_url=HOME, error_code=type(error).__name__))
        history = prior['history'][:]
        semantic = lambda r: tuple(r.get(k) for k in ('release_date','release_time','document_url','document_status','document_kind'))
        changed = []
        for key, row in rows.items():
            if key in before and semantic(row) != semantic(before[key]):
                history.append(dict(event_id=key, replaced_at=stamp, previous=before[key]))
                if row['release_date'] != before[key]['release_date'] or (before[key].get('release_time') is not None and row.get('release_time') is not None and row['release_time'] != before[key]['release_time']):
                    row['schedule_status'] = 'changed'
                changed.append(key)
        scope = dict(confirmed_years=years, dates=sorted({r['release_date'] for r in rows.values()}),
            missing_times=[r['event_id'] for r in rows.values() if not r.get('release_time')],
            errors=errors, captures=captures, changed_events=changed, results_integration='publisher_permission_required')
        check['scope'].update(scope)
        if errors:
            check.update(status='partial' if rows else 'error', error_code='michigan_schedule_sources_unavailable')
        payload = dict(version=1, adapter_version=ADAPTER_VERSION, events=sorted(rows.values(),key=lambda r:r['event_id']), history=history,
            check=dict(status=check['status'] if check['status'] != 'running' else 'success', checked_at=stamp, **scope))
        write_snapshot(payload, Path(path or SNAPSHOT))
    return payload
