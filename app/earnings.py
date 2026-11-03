"""Local manual earnings dates and read-only financial projection; no HTTP or scheduler."""
import argparse
import hashlib
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from app.database.connection import get_independent_connection

NAMESPACE = UUID('11635444-8025-46be-a604-883bce835932')
PILOTS = {'0001045810': ('NVIDIA','NVDA',{'investor.nvidia.com'}),
          '0001018724': ('Amazon','AMZN',{'ir.aboutamazon.com'}),
          '0000050863': ('Intel','INTC',{'www.intel.com','www.intc.com'})}
DATA = Path(__file__).resolve().parents[1] / 'config/earnings_manual.json'
PRECISIONS = {'exact','approximate','after_close','before_open','date_only','unknown'}


def identity(value):
    return str(uuid5(NAMESPACE, value))


def validate(record):
    """Validate only the explicit local record; never discover or fetch a URL."""
    r = json.loads(json.dumps(record))
    if set(r)-{'cik','ticker','fiscal_year','fiscal_quarter','period_label','period_end','release','call'}:
        raise ValueError('Unsupported E2A fields')
    cik = r['cik']
    if cik not in PILOTS: raise ValueError('CIK outside pilot allowlist')
    if r['ticker'] != PILOTS[cik][1]: raise ValueError('Ticker/CIK conflict')
    if not isinstance(r['fiscal_year'],int) or not 1900 <= r['fiscal_year'] <= 2200 or r['fiscal_quarter'] not in (1,2,3,4):
        raise ValueError('Invalid fiscal period')
    if r.get('period_end'): date.fromisoformat(r['period_end'])
    for component in ('release','call'):
        c = r[component]
        precision, status = c['precision'], c['date_status']
        if precision not in PRECISIONS or status not in ('unknown','confirmed','changed','cancelled'):
            raise ValueError('Invalid date status/precision')
        c['scheduled_at_utc'] = c['expected_time_utc'] = None
        if status == 'unknown':
            if precision != 'unknown' or any(c.get(k) for k in ('source_local_date','source_local_time','source_timezone','timezone_label_raw','evidence')):
                raise ValueError('Unknown cannot carry an inferred date or evidence')
            continue
        if precision == 'unknown': raise ValueError('Confirmed dates require precision')
        day = date.fromisoformat(c['source_local_date'])
        evidence = c['evidence']
        url = urlsplit(evidence['source_url'])
        if url.scheme != 'https' or url.hostname not in PILOTS[cik][2] or url.username or url.password or url.port not in (None,443):
            raise ValueError('Unofficial source URL')
        if evidence['cik'] != cik or evidence['fiscal_year'] != r['fiscal_year'] or evidence['fiscal_quarter'] != r['fiscal_quarter']:
            raise ValueError('Evidence company/period conflict')
        if evidence['verification_method'] != 'manually_verified_official_source' or evidence['source_kind'] != 'official_announcement' or not evidence['facts'].strip():
            raise ValueError('Manual official verification required')
        date.fromisoformat(evidence['verified_on'])
        zone = c.get('source_timezone')
        if zone not in ('America/New_York','America/Los_Angeles'): raise ValueError('Invalid publisher IANA timezone')
        if precision in ('exact','approximate'):
            local = datetime.combine(day,time.fromisoformat(c['source_local_time']),ZoneInfo(zone))
            # Reject ambiguous/nonexistent local times, rather than silently choosing a fold.
            if local.utcoffset() != local.replace(fold=1).utcoffset() or local.astimezone(timezone.utc).astimezone(ZoneInfo(zone)).replace(tzinfo=None) != local.replace(tzinfo=None):
                raise ValueError('Ambiguous or nonexistent publisher time')
            label=c.get('timezone_label_raw')
            if label not in (local.tzname(),'PT' if zone.endswith('Los_Angeles') else 'ET'):
                raise ValueError('Timezone abbreviation conflicts with IANA for this date')
            c['scheduled_at_utc' if precision=='exact' else 'expected_time_utc'] = local.astimezone(timezone.utc).isoformat()
        elif c.get('source_local_time'):
            raise ValueError('Session/date-only must not invent a time')
    return r


def import_records(connection, records):
    """Atomic manual import. A stale known confirmation never becomes current again."""
    rows = [validate(r) for r in records]
    with connection.transaction():
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        for r in rows:
            cik=r['cik']; company=identity(cik); period=identity(f"{cik}:{r['fiscal_year']}:{r['fiscal_quarter']}"); event=identity(period+':earnings')
            connection.execute('INSERT INTO earnings_companies VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(company,cik,PILOTS[cik][0],r['ticker']))
            connection.execute('INSERT INTO earnings_company_aliases VALUES (%s,%s) ON CONFLICT DO NOTHING',(company,r['ticker']))
            connection.execute("INSERT INTO earnings_periods VALUES (%s,%s,%s,%s,'quarter',%s,%s) ON CONFLICT DO NOTHING",(period,company,r['fiscal_year'],r['fiscal_quarter'],r['period_label'],r.get('period_end')))
            stored=connection.execute('SELECT period_end,period_label FROM earnings_periods WHERE period_id=%s',(period,)).fetchone()
            if (str(stored[0]) if stored[0] else None,stored[1]) != (r.get('period_end'),r['period_label']):
                raise ValueError('Period metadata conflict requires a separately reviewed correction')
            connection.execute('INSERT INTO earnings_events(event_id,period_id,company_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(event,period,company))
            for component in ('release','call'):
                c=r[component]; encoded=json.dumps(c,sort_keys=True,separators=(',',':')); fingerprint=hashlib.sha256(encoded.encode()).hexdigest()
                confirmation=identity(event+component+fingerprint)
                if connection.execute('SELECT 1 FROM earnings_date_confirmations WHERE confirmation_id=%s',(confirmation,)).fetchone(): continue
                previous=connection.execute('SELECT confirmation_id,date_status,sequence FROM earnings_date_confirmations WHERE event_id=%s AND component=%s ORDER BY sequence DESC LIMIT 1',(event,component)).fetchone()
                if previous and (c['date_status']=='unknown' or (previous[1]!='unknown' and c['date_status'] not in ('changed','cancelled'))):
                    raise ValueError('Date changes require explicit changed/cancelled authorization')
                evidence_id=None
                if c['date_status']!='unknown':
                    evidence_id=identity(event+fingerprint); e=c['evidence']
                    connection.execute('INSERT INTO earnings_source_evidence VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                        (evidence_id,event,company,e['source_url'],e['source_kind'],e['verification_method'],e['verified_on'],e['facts'],fingerprint))
                connection.execute('''INSERT INTO earnings_date_confirmations VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (confirmation,event,company,component,(previous[2]+1 if previous else 1),c['date_status'],c['precision'],c.get('source_local_date'),c.get('source_local_time'),c.get('source_timezone'),c.get('timezone_label_raw'),c['scheduled_at_utc'],c['expected_time_utc'],evidence_id,previous[0] if previous else None))


# Deliberately bounded, manually reviewed session evidence, NOT a perpetual exchange calendar.
# Unknown/holiday/early-close dates do not receive an inferred regular boundary.
SESSION_EVIDENCE = 'https://www.nyse.com/trade/hours-calendars'
REVIEWED_SESSIONS = {'2026-10-29':('09:30','16:00'),'2026-11-17':('09:30','16:00'),
                    '2026-10-22':('09:30','16:00'),'2026-03-16':('09:30','16:00'),
                    '2026-11-27':('09:30','13:00'),'2026-12-24':('09:30','13:00')}


def temporal(c):
    result={k:(v.isoformat() if isinstance(v,(date,datetime,time)) else str(v) if isinstance(v,UUID) else v) for k,v in c.items()}
    instant=c.get('scheduled_at_utc') or c.get('expected_time_utc')
    result['poland_date']=datetime.fromisoformat(str(instant)).astimezone(ZoneInfo('Europe/Warsaw')).date().isoformat() if instant else None
    result['session_boundary_utc']=None
    result['session_boundary_source']=None
    day=str(c.get('source_local_date'))
    if c['precision'] in ('after_close','before_open') and day in REVIEWED_SESSIONS:
        boundary=REVIEWED_SESSIONS[day][1 if c['precision']=='after_close' else 0]
        result['session_boundary_utc']=datetime.combine(date.fromisoformat(day),time.fromisoformat(boundary),ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()
        result['session_boundary_source']=SESSION_EVIDENCE
    return result


def load_events(connection):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute('''SELECT e.event_id,e.company_id,e.publication_status,p.fiscal_year,p.fiscal_quarter,p.period_label,p.period_end,c.cik,c.name,c.ticker
            FROM earnings_events e JOIN earnings_periods p USING(period_id,company_id) JOIN earnings_companies c USING(company_id) ORDER BY c.ticker,p.fiscal_year,p.fiscal_quarter''')
        events=cursor.fetchall()
        cursor.execute('''SELECT d.*,s.source_url,s.source_kind,s.verification_method,s.verified_on,s.facts FROM earnings_date_confirmations d
            LEFT JOIN earnings_source_evidence s USING(evidence_id,event_id,company_id) ORDER BY d.event_id,d.component,d.sequence''')
        confirmations=cursor.fetchall()
    result=[]
    for e in events:
        history=[temporal(c) for c in confirmations if c['event_id']==e['event_id']]
        components={k:next((c for c in reversed(history) if c['component']==k),None) for k in ('release','call')}
        unknown={'date_status':'unknown','precision':'unknown','sequence':0,'source_local_date':None,
                 'source_local_time':None,'source_timezone':None,'timezone_label_raw':None,
                 'scheduled_at_utc':None,'expected_time_utc':None,'poland_date':None,
                 'session_boundary_utc':None,'session_boundary_source':None,'source_url':None,
                 'verified_on':None,'facts':None,'verification_method':None}
        components={k:v or {**unknown,'component':k} for k,v in components.items()}
        result.append({**e,'domain':'earnings','event_id':'earnings:'+str(e['event_id']),'company_id':str(e['company_id']),**components,'history':history})
    from app.earnings_financials import attach
    return attach(connection,result)


def calendar_events(start,end,tickers=None):
    with get_independent_connection() as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        events=load_events(connection)
    selected=[];undated=[]
    for e in events:
        if tickers and e['ticker'] not in tickers: continue
        release=e['release']; call=e['call']
        anchor=release if release and release['date_status']!='unknown' else call
        if not anchor or anchor['date_status']=='unknown':
            if e.get('financial_release_date'):
                if str(start)<=e['financial_release_date']<=str(end): selected.append(e)
            else: undated.append(e)
            continue
        # Source-date bucketing is explicit when no Polish day is established.
        day=anchor['poland_date'] or anchor['source_local_date']
        if str(start)<=day<=str(end): selected.append(e)
    revision=hashlib.sha256(json.dumps(events,default=str,sort_keys=True).encode()).hexdigest()
    def order(e):
        a=e['release'] if e['release']['date_status']!='unknown' else e['call']
        return (a['poland_date'] or a['source_local_date'] or e.get('financial_release_date') or '~',
                a['scheduled_at_utc'] or a['expected_time_utc'] or a['session_boundary_utc'] or '~',e['ticker'],e['event_id'])
    return {'events':sorted(selected,key=order),'undated':sorted(undated,key=order),'earnings_data_revision':revision}


def companies():
    with get_independent_connection() as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute('SELECT company_id,cik,name,ticker FROM earnings_companies ORDER BY ticker,company_id')
            return [{**r,'company_id':str(r['company_id'])} for r in cursor.fetchall()]


def main():
    parser=argparse.ArgumentParser(description='Import local manually verified E2A metadata into an isolated database only')
    parser.add_argument('--input',type=Path,default=DATA)
    args=parser.parse_args()
    from app.database.init_earnings_db import initialize
    with get_independent_connection() as connection:
        initialize(connection)
        import_records(connection,json.loads(args.input.read_text(encoding='utf-8')))


if __name__=='__main__': main()
