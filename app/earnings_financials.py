"""Manually reviewed official quarterly facts. No discovery, HTTP or scheduling.

Fingerprints identify local metadata, never bytes of an archived IR document.
The isolated CLI is intentionally unavailable for the developer's normal database.
"""
import argparse
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from psycopg.rows import dict_row
from app.earnings import PILOTS, identity

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'config/earnings_financial_manual.json'
SCHEMA = ROOT / 'app/database/earnings_financial_schema.sql'
METRICS = {'revenue': ('USD', 'consolidated_revenue'),
           'gaap_diluted_eps': ('USD/share', 'gaap_diluted')}
SCALES = {'USD': Decimal(1), 'USD_millions': Decimal(1000000),
          'USD_billions': Decimal(1000000000), 'USD/share': Decimal(1)}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate(record):
    r = json.loads(json.dumps(record))
    required = {'cik','ticker','fiscal_year','fiscal_quarter','period_label','period_end',
                'release_date','document','observations'}
    if set(r) != required or r['cik'] not in PILOTS or r['ticker'] != PILOTS[r['cik']][1]:
        raise ValueError('Invalid financial company/fields')
    if type(r['fiscal_year']) is not int or not 1900 <= r['fiscal_year'] <= 2200 or type(r['fiscal_quarter']) is not int or r['fiscal_quarter'] not in (1,2,3,4):
        raise ValueError('Invalid fiscal period')
    expected_label = f"Q{r['fiscal_quarter']} " + ('FY' if r['ticker']=='NVDA' else '') + str(r['fiscal_year'])
    if r['period_label'] != expected_label:
        raise ValueError('Fiscal label conflict')
    end, released = date.fromisoformat(r['period_end']), date.fromisoformat(r['release_date'])
    if end > released or released > date.today():
        raise ValueError('Release is not a verified historical report')
    d = r['document']
    if set(d) != {'source_url','document_type','sec_accession','verified_on','evidence_method','source_version','availability_status'}:
        raise ValueError('Unsupported document evidence fields')
    hosts = PILOTS[r['cik']][2] | ({'nvidianews.nvidia.com'} if r['ticker']=='NVDA' else set())
    url = urlsplit(d['source_url'])
    if url.scheme!='https' or url.hostname not in hosts or url.username or url.password or url.port not in (None,443):
        raise ValueError('Unofficial financial source')
    verified = date.fromisoformat(d['verified_on'])
    if not released <= verified <= date.today() or d['document_type']!='earnings_release' or d['evidence_method']!='manual_official_fact_entry' or d['availability_status']!='manually_verified' or not d['source_version'].strip():
        raise ValueError('Official manual earnings-release evidence required')
    if d['sec_accession'] is not None and (not re.fullmatch(r'\d{10}-\d{2}-\d{6}',d['sec_accession']) or not d['sec_accession'].startswith(r['cik'])):
        raise ValueError('SEC accession company conflict')
    if not r['observations'] or len(r['observations'])>2:
        raise ValueError('One or two explicit metrics required')
    seen=set()
    for m in r['observations']:
        if set(m)-{'metric','source_value','source_unit','currency','decimal_places','methodology','correction_reason'}:
            raise ValueError('Unsupported metric fields')
        key=m['metric']
        if key not in METRICS or key in seen or m['currency']!='USD':
            raise ValueError('Invalid metric/currency')
        seen.add(key)
        method='gaap_diluted_attributable_to_intel' if key=='gaap_diluted_eps' and r['ticker']=='INTC' else METRICS[key][1]
        units={'USD','USD_millions','USD_billions'} if key=='revenue' else {'USD/share'}
        if m['methodology']!=method or m['source_unit'] not in units or type(m['decimal_places']) is not int or not 0<=m['decimal_places']<=6:
            raise ValueError('Metric unit/methodology conflict')
        try: value=Decimal(m['source_value'])
        except (InvalidOperation, TypeError, ValueError): raise ValueError('Invalid decimal value')
        if not isinstance(m['source_value'],str) or not value.is_finite() or abs(value)>Decimal('1e16') or (key=='revenue' and value<0) or value.as_tuple().exponent < -m['decimal_places']:
            raise ValueError('Invalid financial precision/value')
        if 'correction_reason' in m and not m['correction_reason'].strip():
            raise ValueError('Empty correction reason')
    return r


def initialize_isolated(connection, expected_signature=None):
    """New schema only in explicitly named E2B sandboxes; normal macrolens refused."""
    name=connection.execute('SELECT current_database()').fetchone()[0]
    if not name.startswith('macrolens_earnings_e2b_'):
        raise ValueError('E2B requires an owned isolated database')
    with connection.transaction():
        existing=connection.execute("SELECT to_regclass('public.earnings_financial_documents'),to_regclass('public.earnings_financial_observations'),to_regprocedure('public.earnings_financial_guard()')").fetchone()
        if any(existing):
            from app.database.activate_earnings import catalog, digest
            if all(existing) and expected_signature and digest(catalog(connection,True))==expected_signature:
                return 'already_initialized'
            raise ValueError('Existing E2B schema requires a matching reviewed signature')
        connection.execute(SCHEMA.read_text(encoding='utf-8'))
        return 'created'


def import_records(connection, records):
    rows=[validate(r) for r in records]
    with connection.transaction():
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        for r in rows:
            company=identity(r['cik']); period=identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}"); event=identity(period+':earnings')
            stored=connection.execute('SELECT company_id,cik,ticker FROM earnings_companies WHERE company_id=%s',(company,)).fetchone()
            if not stored or (str(stored[0]),stored[1],stored[2])!=(company,r['cik'],r['ticker']):
                raise ValueError('Import requires an existing verified E2A company')
            connection.execute("INSERT INTO earnings_periods VALUES(%s,%s,%s,%s,'quarter',%s,%s) ON CONFLICT DO NOTHING",
                (period,company,r['fiscal_year'],r['fiscal_quarter'],r['period_label'],r['period_end']))
            stored=connection.execute('SELECT period_end,period_label FROM earnings_periods WHERE period_id=%s',(period,)).fetchone()
            if (str(stored[0]),stored[1])!=(r['period_end'],r['period_label']):
                raise ValueError('Financial period conflicts with existing E2A metadata')
            connection.execute('INSERT INTO earnings_events(event_id,period_id,company_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(event,period,company))
            document={k:r[k] for k in r if k!='observations'}
            fp=fingerprint(document); doc=identity('financial-document:'+fp); d=r['document']
            connection.execute('''INSERT INTO earnings_financial_documents
                (document_id,company_id,period_id,event_id,cik,period_end,release_date,source_url,document_type,sec_accession,
                 verified_on,evidence_method,source_version,availability_status,record_fingerprint)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                (doc,company,period,event,r['cik'],r['period_end'],r['release_date'],d['source_url'],d['document_type'],d['sec_accession'],d['verified_on'],d['evidence_method'],d['source_version'],d['availability_status'],fp))
            for m in r['observations']:
                fp=fingerprint({'document':doc,'metric':m}); obs=identity('financial-observation:'+fp)
                if connection.execute('SELECT 1 FROM earnings_financial_observations WHERE observation_id=%s',(obs,)).fetchone():
                    continue  # A previously captured record never reactivates an older version.
                prior=connection.execute('SELECT observation_id,version FROM earnings_financial_observations WHERE event_id=%s AND metric=%s ORDER BY version DESC LIMIT 1',(event,m['metric'])).fetchone()
                if prior and not m.get('correction_reason'):
                    raise ValueError('New financial version requires an explicit correction reason')
                if not prior and m.get('correction_reason'):
                    raise ValueError('First observation cannot supersede a missing value')
                connection.execute('''INSERT INTO earnings_financial_observations
                    (observation_id,document_id,event_id,period_id,company_id,metric,actual,currency,unit,source_value,source_unit,decimal_places,methodology,version,supersedes_id,correction_reason,record_fingerprint)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,'USD',%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (obs,doc,event,period,company,m['metric'],Decimal(m['source_value'])*SCALES[m['source_unit']],METRICS[m['metric']][0],Decimal(m['source_value']),m['source_unit'],m['decimal_places'],m['methodology'],prior[1]+1 if prior else 1,prior[0] if prior else None,m.get('correction_reason'),fp))


def attach(connection, events):
    """Add financial data within the caller's read-only snapshot. E2A-only fallback."""
    available=connection.execute("SELECT to_regclass('public.earnings_financial_documents'),to_regclass('public.earnings_financial_observations')").fetchone()
    if any(available) and not all(available):
        raise ValueError('Incomplete financial schema; explicit recovery required')
    rows=[]
    if all(available):
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute('''SELECT o.*,d.source_url,d.document_type,d.sec_accession,d.verified_on,d.evidence_method,
                d.source_version,d.availability_status,d.release_date,d.period_end FROM earnings_financial_observations o
                JOIN earnings_financial_documents d USING(document_id,event_id,period_id,company_id)
                ORDER BY o.event_id,o.metric,o.version''')
            rows=cursor.fetchall()
    by_event={}
    for row in rows:
        by_event.setdefault('earnings:'+str(row['event_id']),[]).append({k:str(v) if v is not None else None for k,v in row.items()})
    for e in events:
        history=by_event.get(e['event_id'],[])
        current={r['metric']:r for r in history}
        e.update(financial_store_status='available' if all(available) else 'not_activated',
                 financial_data_status='complete' if len(current)==2 else 'partial' if current else 'unavailable',
                 revenue_actual=current.get('revenue'),gaap_diluted_eps_actual=current.get('gaap_diluted_eps'),
                 revenue_consensus=None,eps_consensus=None,financial_history=history,
                 financial_release_date=min((r['release_date'] for r in history),default=None),
                 financial_publication_status='published' if history else 'unconfirmed')
    return events


def main():
    parser=argparse.ArgumentParser(description='E2B isolated manual fact import; no external HTTP')
    parser.add_argument('--input',type=Path,default=DATA)
    args=parser.parse_args()
    from app.database.connection import get_independent_connection
    with get_independent_connection() as connection:
        name=connection.execute('SELECT current_database()').fetchone()[0]
        if not name.startswith('macrolens_earnings_e2b_'):
            raise ValueError('Normal database activation is not authorized by this CLI')
        import_records(connection,json.loads(args.input.read_text(encoding='utf-8')))


if __name__=='__main__': main()
