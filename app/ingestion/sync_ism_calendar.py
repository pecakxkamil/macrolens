"""Schedule-only adapter; ISM observations still use import_ism and its tables."""
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse

from app.ingestion.import_ism import Tree, clean, KINDS, parse_report
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'data/derived/ism_calendar_v1.json'
REVIEWED = ROOT / 'config/ism_calendar_evidence.json'
SOURCE_URL = 'https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/'
SCHEDULE_ADAPTER_VERSION = 1


def read_schedule(path=None):
    rows = {}
    check = None
    adapter_version = 0
    for source in ([Path(path)] if path else [REVIEWED, SNAPSHOT]):
        try:
            payload = json.loads(source.read_text(encoding='utf-8'))
            if payload['version'] != 1: continue
            for row in payload.get('events', []):
                if row['kind'] not in KINDS: continue
                key = row['kind'], row['reference_period']
                prior = rows.get(key)
                # A validated response / explicit announcement supersedes a
                # manually reviewed calendar; shorter horizons retain old rows.
                if not prior or (row.get('priority', 0), row['retrieved_at']) >= (prior.get('priority', 0), prior['retrieved_at']):
                    rows[key] = row
            check = payload.get('check') or check
            adapter_version = payload.get('adapter_version',adapter_version)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {'version':1, 'events':list(rows.values()), 'check':check, 'adapter_version':adapter_version}


def parse_calendar(html, rules, retrieved):
    tree = Tree(html)
    text = clean(tree.root.text())
    if not re.search(r'ISM.*(?:Release Dates|release schedule)|Release Dates.*ISM',text) or not re.search(r'10:00\s*a\.m\.\s*\(EST\)', text):
        raise ValueError('ISM calendar clock not confirmed; challenge/error pages are rejected.')
    records = []
    for table in tree.root.all('table'):
        header = clean(table.text())
        if not all(label in header for label in ('Month', 'Manufacturing', 'Services')): continue
        for tr in table.all('tr'):
            cells = [clean(n.text()) for n in tr.children if getattr(n, 'tag', '') in ('td','th')]
            if not cells or not re.fullmatch(r'[A-Za-z]+ 20\d{2}', cells[0]): continue
            if len(cells) != 3: raise ValueError('Incomplete ISM calendar row.')
            month = datetime.strptime(cells[0], '%B %Y').date()
            ordinal = month.year*12+month.month-2
            period = str(date(ordinal//12, ordinal%12+1, 1))
            for i, kind in enumerate(KINDS, 1):
                day = re.fullmatch(r'(\d{1,2})(?:\s*[*\u2020]+)?', cells[i])
                rule = rules.get(kind)
                if not day or not rule or not rule.get('following_month_rule_confirmed') or not rule.get('release_clock_confirmed'):
                    raise ValueError('ISM date or following-month methodology not confirmed.')
                records.append(dict(kind=kind, reference_period=period,
                    release_date=str(date(month.year,month.month,int(day[1]))), release_time='10:00:00',
                    source_timezone='America/New_York', source_url=SOURCE_URL, retrieved_at=retrieved,
                    binding_method='official_ism_calendar_and_month_rule', priority=3,
                    period_rule_source=rule['source_url'], period_rule_document_hash=rule['raw_hash'],
                    clock_source_url=rule['source_url'],
                    retrieval_method='backend_http', clock_note='Calendar clock corroborated by ISM report prose specifying ET.'))
    if not records or len({(r['kind'],r['reference_period']) for r in records}) != len(records):
        raise ValueError('Missing or conflicting ISM calendar rows.')
    return records


def stored_report_rules(connection):
    with connection.cursor() as cursor:
        cursor.execute('''SELECT DISTINCT ON(series_id) series_id,source_url,raw_path,raw_hash,retrieved_at
            FROM ism_documents ORDER BY series_id,report_month DESC,published_at DESC,retrieved_at DESC,id DESC''')
        rows = cursor.fetchall()
    rules = {}
    for sid, url, raw_path, digest, retrieved in rows:
        kind = next((k for k,v in KINDS.items() if v==sid), None)
        if not kind: continue
        # import_ism stores paths relative to data/, not to the project root.
        data_root = (ROOT/'data').resolve()
        path = (data_root/str(raw_path).replace('\\','/')).resolve()
        if data_root not in path.parents: continue
        try:
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != digest: continue
            rules[kind] = {**parse_report(content.decode('utf-8'),kind), 'source_url':url,'raw_hash':digest,'retrieved_at':retrieved}
        except (OSError,ValueError,UnicodeError):
            continue
    return rules


def apply_announcements(events, rules, stamp):
    announcements=[]
    for kind, report in rules.items():
        row=report.get('next_release')
        if not row:continue
        key=kind,row['reference_period']
        retrieved=report.get('retrieved_at')
        receipt=dict(kind=kind, **row, source_url=report['source_url'],
            retrieved_at=retrieved.isoformat() if retrieved else stamp,
            document_published_at=report['published_at'].isoformat(),raw_hash=report['raw_hash'],
            binding_method='explicit_next_ism_report',retrieval_method='stored_validated_document',priority=2)
        announcements.append(receipt)
        prior=events.get(key)
        if not prior or prior.get('priority',0)<3 or datetime.fromisoformat(receipt['document_published_at'])>datetime.fromisoformat(prior['retrieved_at']):
            events[key]=receipt
    return announcements


def write_snapshot(payload, target):
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(payload,indent=2),encoding='utf-8');temporary.replace(target)


def rebuild_cached_announcements(connection, now=None, path=None):
    """Invalidate derived schedule metadata after import, without provider calls.

    Preserve the annual source check and original document retrieval timestamps;
    this is not another successful network check and does not reset its cadence.
    """
    now=now or datetime.now(timezone.utc)
    payload=read_schedule(path)
    events={(r['kind'],r['reference_period']):r for r in payload['events']}
    announcements=apply_announcements(events,stored_report_rules(connection),now.isoformat())
    payload.update(events=list(events.values()),announcements=announcements,
        adapter_version=SCHEDULE_ADAPTER_VERSION,assembled_at=now.isoformat())
    write_snapshot(payload,Path(path or SNAPSHOT))
    return payload


def sync_schedule(client, connection, now=None, path=None, rules=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    target = Path(path or SNAPSHOT)
    prior = read_schedule(path)
    rules = stored_report_rules(connection) if rules is None else rules
    events = {(r['kind'],r['reference_period']):r for r in prior['events']}
    raw_root = ROOT/'data/raw/ism/calendar'
    raw_root.mkdir(parents=True,exist_ok=True)
    with availability_check('ism:calendar', {'provider':'ISM', 'source_url':SOURCE_URL}) as check:
        annual_status = 'error'
        try:
            before_request('ISM')
            response = client.get(SOURCE_URL)
            check['scope']['annual_http_status']=response.status_code
            capture = raw_root/(f'{now:%Y%m%dT%H%M%S}-{uuid4().hex}.html')
            capture.write_bytes(response.content)
            response.raise_for_status()
            if urlparse(str(response.url)).hostname != 'www.ismworld.org':raise ValueError('Unexpected ISM redirect host.')
            if 'text/html' not in response.headers.get('content-type','').lower(): raise ValueError('Expected ISM HTML calendar.')
            for row in parse_calendar(response.text,rules,stamp):
                row.update(raw_hash=hashlib.sha256(response.content).hexdigest(), capture_path=str(capture.relative_to(ROOT)))
                events[(row['kind'],row['reference_period'])] = row
            annual_status = 'success'
        except Exception as error:
            check['scope']['annual_error_code'] = type(error).__name__
        announcements = apply_announcements(events,rules,stamp)
        check['scope'].update(annual_schedule_status=annual_status, announcements=announcements,
            dates=sorted({e['release_date'] for e in events.values()}),
            confirmed_from=min((e['release_date'] for e in events.values()),default=None),
            confirmed_through=max((e['release_date'] for e in events.values()),default=None))
        if annual_status != 'success': check.update(status='partial',error_code='ism_annual_calendar_unavailable')
        payload={'version':1,'adapter_version':SCHEDULE_ADAPTER_VERSION,'events':list(events.values()),'announcements':announcements,'check':dict(status='success' if annual_status=='success' else 'partial',
            attempted_at=stamp,**check['scope'])}
        write_snapshot(payload,target)
    return payload
