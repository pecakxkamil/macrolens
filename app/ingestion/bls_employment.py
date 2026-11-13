"""Bounded BLS Employment Situation batches. No schema initialization or GET writes."""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from email.utils import parsedate_to_datetime
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL

import httpx
from psycopg.types.json import Jsonb

URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
SOURCE = 'bls:employment'
LOCK = 726530033
MAX_BYTES = 2 * 1024 * 1024
CONTRACT = {
    'PAYEMS': ('CES0000000001', 'monthly_change', 'thousand jobs', 'thousands of persons'),
    'UNRATE': ('LNS14000000', 'raw', 'percent', 'percent'),
    'CES0500000003': ('CES0500000003', 'mom', 'percent', 'dollars per hour'),
    'CIVPART': ('LNS11300000', 'raw', 'percent', 'percent'),
    'U6RATE': ('LNS13327709', 'raw', 'percent', 'percent'),
    'AWHAETP': ('CES0500000002', 'raw', 'hours', 'hours'),
}
POLICY = dict(release_id=50, source=SOURCE, url=URL, series=CONTRACT,
              interval_seconds=900, window_seconds=7200, rolling_daily_calls=8,
              timeout_seconds=25, max_bytes=MAX_BYTES, seasonal_adjustment='SA',
              storage='publisher_documents only; never overwrite FRED/ALFRED',
              publication_precision='scheduled release; availability is HTTP capture, not proven first print')


def instant(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def parse(raw, period):
    payload = json.loads(raw)
    observed = date.fromisoformat(period)
    if observed.day != 1 or payload.get('status') != 'REQUEST_SUCCEEDED':
        raise ValueError('Unconfirmed BLS response/period')
    rows = payload.get('Results', {}).get('series', [])
    expected = {v[0] for v in CONTRACT.values()}
    if len(rows) != 6 or {r.get('seriesID') for r in rows} != expected:
        raise ValueError('Missing, duplicated or unexpected BLS series')
    result = {}; previous = (observed-timedelta(days=1)).replace(day=1)
    earlier = (previous-timedelta(days=1)).replace(day=1)
    for sid, (bls, feature, unit, input_unit) in CONTRACT.items():
        series = next(r for r in rows if r['seriesID'] == bls)
        if series.get('seasonal_adjustment', 'SA') != 'SA' or series.get('unit', input_unit) != input_unit:
            raise ValueError('BLS basis differs from reviewed series contract')
        points = {}
        for row in series['data']:
            code = row.get('period', '')
            if code == 'M13': continue
            if len(code) != 3 or code[0] != 'M' or not code[1:].isdigit() or not 1 <= int(code[1:]) <= 12:
                raise ValueError('Invalid monthly BLS observation')
            key = str(date(int(row['year']), int(code[1:]), 1))
            try: value = Decimal(row['value'])
            except (InvalidOperation, TypeError): raise ValueError('Invalid BLS number') from None
            if key in points or not value.is_finite() or value < 0 or (unit == 'percent' and feature == 'raw' and value > 100):
                raise ValueError('Invalid/duplicate BLS level')
            points[key] = dict(value=str(value), footnotes=row.get('footnotes', []))
        required = [str(observed), str(previous)] + ([str(earlier)] if feature != 'raw' else [])
        if any(p not in points for p in required): raise ValueError('Incomplete BLS transformation dependencies')
        def value(p): return Decimal(points[str(p)]['value'])
        current, prior = value(observed), value(previous)
        method = 'published SA level'; unrounded = None
        if feature == 'monthly_change':
            current, prior = current-prior, prior-value(earlier)
            method = 'difference of same-document SA payroll levels'
        if feature == 'mom':
            if not prior or not value(earlier): raise ValueError('Zero wage denominator')
            unrounded = (current/prior-1)*100
            current = unrounded.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            prior = ((prior/value(earlier)-1)*100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            method = 'derived MoM from published SA dollar levels; rounded 1 decimal'
        trend={}
        for key in sorted(points):
            previous_key=str((date.fromisoformat(key)-timedelta(days=1)).replace(day=1))
            n=Decimal(points[key]['value'])
            if feature!='raw':
                if previous_key not in points:continue
                denominator=Decimal(points[previous_key]['value'])
                if feature=='monthly_change':n-=denominator
                elif denominator:n=((n/denominator-1)*100).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP)
                else:continue
            trend[key]=str(n)
        result[sid] = dict(series_id=sid, bls_series_id=bls, feature_name=feature, unit=unit,
            input_unit=input_unit, seasonal_adjustment='SA', actual=str(current), previous=str(prior),
            reference_period=period, previous_period=str(previous), method=method,
            unrounded_actual=str(unrounded) if unrounded is not None else None,
            inputs={p:points[p] for p in required}, history=points, trend=trend)
    return result


def events(now):
    from app.analytics.release_calendar import list_calendar_events
    from app.analytics.calendar_evidence import read_evidence, period_evidence
    from app.analytics.employment_measures import expand_employment_evidence
    evidence = expand_employment_evidence(read_evidence()); result = []
    for e in list_calendar_events(now.date()-timedelta(days=1), now.date())['events']:
        if e.get('release_id') != 50 or not e.get('release_datetime_utc'): continue
        schedule = instant(e['release_datetime_utc'])
        if not schedule <= now < schedule+timedelta(seconds=POLICY['window_seconds']): continue
        proofs = [period_evidence(evidence,50,str(e['release_date']),sid) for sid in CONTRACT]
        if not all(p and p.get('source_url','').startswith('https://www.bls.gov/') for p in proofs): continue
        periods = {p['reference_period'] for p in proofs}
        if len(periods) != 1: continue
        period = periods.pop()
        if date.fromisoformat(period) >= schedule.date(): continue
        result.append(dict(release_id=50, release_date=str(e['release_date']), reference_period=period,
            scheduled_at=schedule.isoformat(), schedule_proofs=proofs))
    return result


def documents(c):
    result=[]
    for i,url,stamp,sha,meta in c.execute("SELECT id,source_url,retrieved_at,raw_hash,metadata FROM publisher_documents WHERE source=%s AND kind='employment-batch' ORDER BY retrieved_at,id",(SOURCE,)):
        try:
            raw=meta['raw_utf8'].encode('utf-8')
            if url!=URL or hashlib.sha256(raw).hexdigest()!=sha or meta['contract']!=json.loads(json.dumps(POLICY)):continue
            if parse(raw,meta['event']['reference_period'])!=meta['readings']:continue
        except (ValueError,KeyError,TypeError):continue
        result.append(dict(id=str(i),source_url=url,retrieved_at=stamp,raw_hash=sha,metadata=meta))
    return result


def complete(c, event):
    return any(all(d['metadata']['event'].get(k)==event.get(k) for k in ('release_id','release_date','reference_period','scheduled_at')) and d['metadata'].get('readings') for d in documents(c))


def retry_after(value, now):
    try: return now+timedelta(seconds=max(0,int(value)))
    except (ValueError,TypeError):
        try: return parsedate_to_datetime(value).astimezone(timezone.utc)
        except (ValueError,TypeError,OverflowError): return now+timedelta(hours=24)


def fetch(client, event):
    period = date.fromisoformat(event['reference_period'])
    first = (period-timedelta(days=62)).year
    request = dict(seriesid=[v[0] for v in CONTRACT.values()],startyear=str(first),endyear=str(period.year))
    with client.stream('POST',URL,json=request) as response:
        # No redirects, key, HTML fallback, identity rotation or immediate retries.
        if response.status_code != 200:
            return None, request, response.status_code, response.headers.get('Retry-After')
        chunks=[];size=0
        for chunk in response.iter_bytes():
            size+=len(chunk)
            if size>MAX_BYTES: raise ValueError('BLS response too large')
            chunks.append(chunk)
        return b''.join(chunks),request,200,None


def run(factory, token, directory, now=None, client=None, events_loader=events, crash_after_claim=False):
    from app.database.forecast_f1_authorization_bls import authorized
    now = now or datetime.now(timezone.utc)
    with factory() as c:
        c.read_only=True; authorized(c,token)
        candidates=events_loader(now)
    if not candidates: return dict(status='outside_release_window',added=0)
    with factory() as c:
        c.autocommit=True
        if not c.execute('SELECT pg_try_advisory_lock(%s)',(LOCK,)).fetchone()[0]: return dict(status='busy',added=0)
        try:
            event=candidates[0]; key=event['release_date']+':'+event['reference_period']
            if complete(c,event): return dict(status='complete',added=0)
            if token.get('version') in (4,5):
                from app.ingestion.bls_budget import claim as shared_claim
                claim,scope,blocked=shared_claim(c,SOURCE,event,now)
                if blocked:return dict(status=blocked,added=0)
            else:
                # The independent durable row counts errors/interrupted calls too.
                rows=c.execute("SELECT attempted_at,scope FROM source_check_runs WHERE resource=%s AND (attempted_at>%s OR (scope->>'retry_at')::timestamptz>%s) ORDER BY attempted_at DESC",(SOURCE,now-timedelta(days=1),now)).fetchall()
                deadlines=[instant(r[1]['retry_at']) for r in rows if r[1].get('retry_at')]
                if sum(r[0]>now-timedelta(days=1) for r in rows)>=POLICY['rolling_daily_calls']: return dict(status='daily_limit',added=0)
                if deadlines and max(deadlines)>now: return dict(status='cooldown',added=0)
                claim=uuid4(); scope=dict(event=event,key=key,retry_at=(now+timedelta(minutes=15)).isoformat(),phase='claimed_before_http')
                c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,status,scope) VALUES(%s,%s,%s,'running',%s)",(claim,SOURCE,now,Jsonb(scope)))
            if crash_after_claim: raise RuntimeError('Injected crash after durable claim')
            owned=client is None
            if owned: client=httpx.Client(timeout=25,follow_redirects=False)
            try:
                raw,request,status,retry=fetch(client,event)
                captured=datetime.now(timezone.utc)
                if status!=200:
                    until=max(captured+timedelta(minutes=15),retry_after(retry,captured) if retry else captured+timedelta(hours=24))
                    scope.update(retry_at=until.isoformat(),http_status=status,phase='http_refused')
                    c.execute("UPDATE source_check_runs SET finished_at=%s,status='error',error_code='bls_http_refused',scope=%s WHERE id=%s",(captured,Jsonb(scope),claim))
                    return dict(status='http_refused',added=0)
                readings=parse(raw,event['reference_period']);sha=hashlib.sha256(raw).hexdigest()
                # Original bytes are immutable; a database failure can leave an unreferenced RAW, not a fake SQL receipt.
                directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);path=directory/(sha+'.json')
                if path.exists():
                    if path.read_bytes()!=raw: raise ValueError('RAW fingerprint conflict')
                else:
                    with path.open('xb') as f:f.write(raw)
                meta=dict(version=1,event=event,readings=readings,request=request,contract=POLICY,raw_utf8=raw.decode('utf-8'),
                          source='BLS Public API',availability='current_at_capture; not proven first print')
                identifier=uuid5(NAMESPACE_URL,SOURCE+':'+key+':'+sha)
                with c.transaction():
                    authorized(c,token)
                    c.execute("INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata) VALUES(%s,%s,'employment-batch',%s,%s,200,%s,%s,%s) ON CONFLICT(source,kind,raw_hash) DO NOTHING",(identifier,SOURCE,URL,captured,sha,str(path),Jsonb(meta)))
                    scope.update(phase='stored',raw_hash=sha,document_id=str(identifier),http_status=200)
                    c.execute("UPDATE source_check_runs SET finished_at=%s,status='success',scope=%s WHERE id=%s",(captured,Jsonb(scope),claim))
                return dict(status='complete',added=1,raw_hash=sha)
            except Exception:
                c.execute("UPDATE source_check_runs SET finished_at=clock_timestamp(),status='error',error_code='bls_unconfirmed' WHERE id=%s",(claim,))
                raise
            finally:
                if owned:client.close()
        finally:c.execute('SELECT pg_advisory_unlock(%s)',(LOCK,))


def project(events, c, now):
    docs=documents(c)
    for event in events:
        if event.get('release_id')!=50:continue
        matching=[d for d in docs if d['retrieved_at']<=now and d['metadata']['event']['release_date']==str(event['release_date'])
                  and instant(d['metadata']['event']['scheduled_at'])<=now]
        if not matching:continue
        doc=matching[-1];meta=doc['metadata']
        for m in event.get('measures',[]):
            row=meta['readings'].get(m['series_id'])
            if not row or m['feature_name']!=row['feature_name'] or m.get('unit')!=row['unit'] or m.get('reference_period')!=row['reference_period']:continue
            original={k:m.get(k) for k in ('actual','previous','actual_provenance','previous_provenance','data_version')}
            proof=dict(source=SOURCE,source_url=URL,document_id=doc['id'],raw_hash=doc['raw_hash'],retrieved_at=doc['retrieved_at'].isoformat(),
                observation_period=row['reference_period'],version='captured_snapshot',method=row['method'],unit=row['unit'],
                inputs=row['inputs'],publication_precision='capture',first_print=False)
            m.update(actual=float(row['actual']),previous=float(row['previous']),data_version='official_release',previous_data_version='official_release',
                previous_period=row['previous_period'],previous_kind='previous_period',source_url=URL,selected_source=SOURCE,
                result_status='available',actual_provenance=proof,previous_provenance={**proof,'observation_period':row['previous_period'],'version':'revised_same_capture'},
                result_provenance=proof,fred_alternative=original,comparison_status='same_bls_capture',revision_confirmed=original['previous'] is not None and Decimal(row['previous'])!=Decimal(str(original['previous'])),
                missing_reason={'actual':None,'previous':None},bls_history=row['trend'],bls_method=row['method'],seasonal_adjustment='SA')
    return events
