"""Reviewed historical financial snapshots. No events, HTTP or normal DB import."""
import json
from pathlib import Path
from decimal import Decimal
from psycopg.types.json import Jsonb
from app.earnings import identity
from app.earnings_financials import fingerprint

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'config/earnings_previous_reviewed.json'
SCHEMA=ROOT/'app/database/earnings_history_schema.sql'
PREFIX='macrolens_earnings_e2b_e2c_e2d_e2e_'
SCALES={'units':1,'thousands':1000,'millions':1000000,'billions':1000000000,'per_share':1}


def validate(record):
    # Every imported snapshot must exactly match the independently reviewed
    # local ledger, including basis, precision, source and verified date.
    reviewed=json.loads(DATA.read_text(encoding='utf-8'))
    if record not in reviewed or not record['observations']:
        raise ValueError('Historical snapshot is absent from reviewed ledger')
    result=json.loads(json.dumps(record))
    for metric in result['observations']:
        value=Decimal(metric['source_value'])
        if not value.is_finite():raise ValueError('Non-finite historical metric')
        metric['actual']=str(value*SCALES[metric['source_unit']])
    return result


def initialize_isolated(connection, expected_signature=None):
    if not connection.info.dbname.startswith(PREFIX):raise ValueError('E2E history requires owned isolation')
    from app.database.activate_earnings import digest,catalog
    with connection.transaction():
        objects=connection.execute("SELECT to_regclass('public.earnings_historical_reports'),to_regprocedure('public.earnings_history_guard()')").fetchone()
        if any(objects):
            if all(objects) and expected_signature and digest(catalog(connection,True))==expected_signature:return 'already_initialized'
            raise ValueError('Partial/foreign history schema; reviewed signature required')
        connection.execute(SCHEMA.read_text(encoding='utf-8'))
    return 'created'


def import_records(connection, records):
    if not connection.info.dbname.startswith(PREFIX):raise ValueError('Historical import rejects normal database')
    prepared=[validate(r) for r in records]
    keys=[(r['cik'],r['fiscal_year'],r['fiscal_quarter']) for r in prepared]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate historical period in batch')
    with connection.transaction():
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        for r in prepared:
            fp=fingerprint(r)
            if connection.execute('SELECT 1 FROM earnings_historical_reports WHERE record_fingerprint=%s',(fp,)).fetchone():continue
            company=identity(r['cik'])
            prior=connection.execute('SELECT document_id,version FROM earnings_historical_reports WHERE company_id=%s AND fiscal_year=%s AND fiscal_quarter=%s ORDER BY version DESC LIMIT 1',(company,r['fiscal_year'],r['fiscal_quarter'])).fetchone()
            if bool(prior)!=bool(r.get('correction_reason')):raise ValueError('Historical revision requires a correction reason')
            connection.execute('''INSERT INTO earnings_historical_reports(document_id,company_id,cik,fiscal_year,fiscal_quarter,version,supersedes_id,correction_reason,record_fingerprint,payload)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(identity('historical:'+fp),company,r['cik'],r['fiscal_year'],r['fiscal_quarter'],prior[1]+1 if prior else 1,prior[0] if prior else None,r.get('correction_reason'),fp,Jsonb(r)))


def load(connection):
    objects=connection.execute("SELECT to_regclass('public.earnings_historical_reports'),to_regprocedure('public.earnings_history_guard()')").fetchone()
    if not any(objects):return [],'not_activated'
    if not all(objects):raise ValueError('Incomplete historical store')
    rows=connection.execute('SELECT company_id,payload,version,captured_at,document_id FROM earnings_historical_reports ORDER BY company_id,fiscal_year,fiscal_quarter,version').fetchall()
    result=[]
    for company,r,version,captured,document in rows:
        metrics={m['metric']:{**m,**{k:r[k] for k in ('source_url','document_type','verified_on','release_date','period_end')},'version':str(version),'captured_at':str(captured),'document_id':str(document)} for m in r['observations']}
        result.append({**r,'company_id':str(company),'reported_eps_actual':metrics.get('reported_diluted_eps'),'revenue_actual':metrics.get('revenue'),'historical_version':version})
    return result,'available'
