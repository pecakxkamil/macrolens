"""Reviewed issuer registry and manual dates. No HTTP, scheduler or normal-DB CLI."""
import argparse
import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from app import earnings as dates
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'config/earnings_companies_reviewed.json'
DATA = ROOT / 'config/earnings_dates_reviewed.json'
SCHEMA = ROOT / 'app/database/earnings_coverage_schema.sql'
ZONE_ORDER = ('America/New_York','America/Los_Angeles','America/Chicago','America/Denver',
              'America/Toronto','Europe/Amsterdam','Europe/London','Asia/Taipei','Etc/UTC')
ZONES = set(ZONE_ORDER)


def initialize_isolated(connection):
    if not connection.info.dbname.startswith('macrolens_earnings_e2b_e2c_'):
        raise ValueError('Timezone migration requires an owned isolated E2C database')
    with connection.transaction():
        definition=connection.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='earnings_date_confirmations'::regclass AND conname='earnings_date_confirmations_source_timezone_check'").fetchone()
        def expected(zones):
            return "CHECK ((source_timezone = ANY (ARRAY["+', '.join("'"+z+"'::text" for z in zones)+"])))"
        if definition and definition[0]==expected(ZONE_ORDER): return 'already_initialized'
        if not definition or definition[0]!=expected(ZONE_ORDER[:2]):
            raise ValueError('Unexpected timezone constraint; separate review required')
        connection.execute(SCHEMA.read_text(encoding='utf-8'))
        return 'created'


def registry():
    rows = json.loads(REGISTRY.read_text(encoding='utf-8'))
    ciks, aliases = set(), set()
    for row in rows:
        if not re.fullmatch(r'\d{10}', row['cik']) or row['cik'] in ciks:
            raise ValueError('Duplicate or invalid issuer CIK')
        if not row['identity_source'].startswith('https://www.sec.gov/'):
            raise ValueError('Reviewed SEC identity evidence required')
        if row['ticker'] not in row['aliases'] or len(row['aliases']) != len(set(row['aliases'])):
            raise ValueError('Canonical ticker and unique aliases required')
        for symbol in row['aliases']:
            if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}', symbol) or symbol in aliases:
                raise ValueError('Alias assigned to multiple issuers')
            aliases.add(symbol)
        ciks.add(row['cik'])
    return {r['cik']: r for r in rows}


def validate(record, companies=None):
    companies = registry() if companies is None else companies
    r = json.loads(json.dumps(record))
    if set(r) != {'cik','ticker','fiscal_year','fiscal_quarter','period_label','period_end','release','call'}:
        raise ValueError('Only reviewed date metadata accepted; no financial fields')
    company = companies.get(r['cik'])
    if not company or r['ticker'] not in company['aliases']:
        raise ValueError('Unreviewed CIK or ticker/CIK conflict')
    if type(r['fiscal_year']) is not int or not 1900 <= r['fiscal_year'] <= 2200 or type(r['fiscal_quarter']) is not int or r['fiscal_quarter'] not in (1,2,3,4):
        raise ValueError('Invalid fiscal year/quarter')
    if not r['period_label'].strip(): raise ValueError('Fiscal label required')
    if r['period_end']: date.fromisoformat(r['period_end'])
    period={k:r[k] for k in ('fiscal_year','fiscal_quarter','period_label','period_end')}
    if period not in company['reviewed_periods']:
        raise ValueError('Fiscal period not present in the reviewed issuer ledger')
    for key in ('release','call'):
        c = r[key]
        if set(c)-{'date_status','precision','source_local_date','source_local_time','source_timezone','timezone_label_raw','evidence'}:
            raise ValueError('Unsupported date component fields')
        status, precision = c['date_status'], c['precision']
        if status not in ('unknown','confirmed','changed','cancelled') or precision not in dates.PRECISIONS:
            raise ValueError('Invalid confirmation status/precision')
        c['scheduled_at_utc'] = c['expected_time_utc'] = None
        if status == 'unknown':
            if precision != 'unknown' or any(c.get(k) for k in ('source_local_date','source_local_time','source_timezone','timezone_label_raw','evidence')):
                raise ValueError('Undated components cannot carry dates/evidence')
            continue
        if precision == 'unknown': raise ValueError('Dated evidence requires explicit precision')
        day = date.fromisoformat(c['source_local_date'])
        proof = c['evidence']; url = urlsplit(proof['source_url'])
        if url.scheme != 'https' or url.hostname not in company['official_hosts'] or url.username or url.password or url.port not in (None,443) or url.fragment:
            raise ValueError('Unofficial evidence URL')
        if (proof['cik'],proof['fiscal_year'],proof['fiscal_quarter'],proof['period_label'],proof['period_end']) != (r['cik'],r['fiscal_year'],r['fiscal_quarter'],r['period_label'],r['period_end']):
            raise ValueError('Evidence fiscal period/issuer conflict')
        if proof['verification_method'] != 'manually_verified_official_source' or proof['source_kind'] != 'official_announcement' or not proof['facts'].strip():
            raise ValueError('Reviewed official evidence required')
        date.fromisoformat(proof['verified_on'])
        if proof['document_type'] not in ('earnings_release','earnings_date_announcement'):
            raise ValueError('Unsupported evidence kind')
        if precision in ('exact','approximate'):
            zone = c.get('source_timezone')
            if zone not in ZONES:
                raise ValueError('Unreviewed source IANA timezone')
            local = datetime.combine(day,time.fromisoformat(c['source_local_time']),ZoneInfo(zone))
            if local.utcoffset()!=local.replace(fold=1).utcoffset() or local.astimezone(timezone.utc).astimezone(ZoneInfo(zone)).replace(tzinfo=None)!=local.replace(tzinfo=None):
                raise ValueError('Ambiguous or nonexistent source time')
            generic={'America/New_York':'ET','America/Los_Angeles':'PT','America/Chicago':'CT','America/Denver':'MT','America/Toronto':'ET','Etc/UTC':'GMT'}
            if not c.get('timezone_label_raw') or c['timezone_label_raw'] not in (local.tzname(),generic.get(zone),zone):
                raise ValueError('Timezone label conflicts with IANA')
            c['scheduled_at_utc' if precision=='exact' else 'expected_time_utc'] = local.astimezone(timezone.utc).isoformat()
        elif c.get('source_local_time') or c.get('source_timezone') not in (None,*ZONES):
            raise ValueError('Date/session evidence must not invent a timed instant')
        if precision in ('after_close','before_open') and c.get('source_timezone') != 'America/New_York':
            raise ValueError('US session windows require New York semantics')
    if all(r[k]['date_status']=='unknown' for k in ('release','call')):
        raise ValueError('Register the issuer without generating an undated event')
    return r


def import_records(connection, records):
    companies = registry()
    rows = [validate(r,companies) for r in records]
    keys = [(r['cik'],r['fiscal_year'],r['fiscal_quarter']) for r in rows]
    if len(keys)!=len(set(keys)): raise ValueError('Duplicate issuer/quarter in batch')
    with connection.transaction():
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        for cik, company in companies.items():
            cid = dates.identity(cik)
            stored = connection.execute('SELECT company_id,ticker FROM earnings_companies WHERE cik=%s',(cik,)).fetchone()
            if stored and (str(stored[0])!=cid or stored[1]!=company['ticker']):
                raise ValueError('Existing issuer identity differs from registry')
            for alias in company['aliases']:
                if connection.execute('SELECT 1 FROM earnings_company_aliases WHERE ticker=%s AND company_id<>%s',(alias,cid)).fetchone() or connection.execute('SELECT 1 FROM earnings_companies WHERE ticker=%s AND company_id<>%s',(alias,cid)).fetchone():
                    raise ValueError('Alias already belongs to another issuer')
            connection.execute('INSERT INTO earnings_companies VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(cid,cik,company['name'],company['ticker']))
            for alias in company['aliases']:
                connection.execute('INSERT INTO earnings_company_aliases VALUES (%s,%s) ON CONFLICT DO NOTHING',(cid,alias))
        for r in rows:
            cid = dates.identity(r['cik'])
            period = dates.identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}")
            event = dates.identity(period+':earnings')
            connection.execute("INSERT INTO earnings_periods VALUES (%s,%s,%s,%s,'quarter',%s,%s) ON CONFLICT DO NOTHING",(period,cid,r['fiscal_year'],r['fiscal_quarter'],r['period_label'],r['period_end']))
            stored = connection.execute('SELECT period_label,period_end FROM earnings_periods WHERE period_id=%s',(period,)).fetchone()
            if (stored[0],str(stored[1]) if stored[1] else None)!=(r['period_label'],r['period_end']):
                raise ValueError('Existing fiscal period differs; correction requires separate review')
            connection.execute('INSERT INTO earnings_events(event_id,period_id,company_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(event,period,cid))
            for component in ('release','call'):
                c=r[component]; encoded=json.dumps(c,sort_keys=True,separators=(',',':'))
                fingerprint=hashlib.sha256(encoded.encode()).hexdigest()
                confirmation=dates.identity(event+component+fingerprint)
                if connection.execute('SELECT 1 FROM earnings_date_confirmations WHERE confirmation_id=%s',(confirmation,)).fetchone(): continue
                previous=connection.execute('SELECT confirmation_id,date_status,sequence FROM earnings_date_confirmations WHERE event_id=%s AND component=%s ORDER BY sequence DESC LIMIT 1',(event,component)).fetchone()
                if previous and (c['date_status']=='unknown' or (previous[1]!='unknown' and c['date_status'] not in ('changed','cancelled'))):
                    raise ValueError('Changes require explicit changed/cancelled evidence')
                evidence=None
                if c['date_status']!='unknown':
                    evidence=dates.identity(event+fingerprint); proof=c['evidence']
                    # Metadata fingerprint, never a hash/receipt of an IR document.
                    facts=proof['facts']+' | '+proof['document_type']+' | '+r['period_label']
                    connection.execute('INSERT INTO earnings_source_evidence VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(evidence,event,cid,proof['source_url'],proof['source_kind'],proof['verification_method'],proof['verified_on'],facts,fingerprint))
                connection.execute('INSERT INTO earnings_date_confirmations VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(confirmation,event,cid,component,previous[2]+1 if previous else 1,c['date_status'],c['precision'],c.get('source_local_date'),c.get('source_local_time'),c.get('source_timezone'),c.get('timezone_label_raw'),c['scheduled_at_utc'],c['expected_time_utc'],evidence,previous[0] if previous else None))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file',type=Path,default=DATA)
    args=parser.parse_args()
    with get_independent_connection() as connection:
        if not connection.info.dbname.startswith('macrolens_earnings_e2b_e2c_'):
            raise ValueError('Coverage CLI is restricted to owned isolated E2C databases')
        with connection.transaction():
            initialize_isolated(connection)
            import_records(connection,json.loads(args.file.read_text(encoding='utf-8')))


if __name__=='__main__': main()
