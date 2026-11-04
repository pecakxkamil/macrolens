"""Reviewed whole-issuer USD market cap snapshots. No network or automatic feed.

No production source is approved yet. The empty reviewed ledger deliberately
imports nothing. Price/share/FX calculations require a separately reviewed
model and are rejected rather than inferred from EPS, float or ADR counts.
"""
import json
from datetime import date,datetime,timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
from psycopg.rows import dict_row
from app.earnings import identity
from app.earnings_financials import fingerprint

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'config/earnings_market_cap_reviewed.json'
SCHEMA=ROOT/'app/database/earnings_market_cap_schema.sql'
PREFIX='macrolens_earnings_e2b_e2c_e2d_e2e_cap_'
FIELDS={'cik','market_cap_usd','currency','as_of','measured_at','source_url','source_id','source_version','method','issuer_scope','basis_evidence','access_evidence','verified_on'}
MAX_AGE_DAYS=7


def utc_today():
    return datetime.now(timezone.utc).date()


def is_fresh(as_of,today=None):
    age=((today or utc_today())-date.fromisoformat(str(as_of))).days
    return 0<=age<=MAX_AGE_DAYS


def measurement_basis(value):
    """Keep first-fetch receipts without creating versions for later polling."""
    try:
        evidence=json.loads(value)
        if isinstance(evidence,dict) and evidence.get('provider')=='FMP':
            return {k:v for k,v in evidence.items() if k not in ('retrieved_at','receipts')}
    except (ValueError,TypeError):pass
    return value


def access_is_current(evidence):
    basis=measurement_basis(evidence)
    if isinstance(basis,dict) and basis.get('provider')=='FMP':
        try:return utc_today()<=date.fromisoformat(basis['access_valid_until'])
        except (ValueError,KeyError,TypeError):return False
    return True


def validate(record,reviewed_path=None):
    if set(record)!=FIELDS:raise ValueError('Explicit dated market cap provenance required')
    if record not in json.loads((reviewed_path or DATA).read_text(encoding='utf-8')):
        raise ValueError('Unreviewed market cap source, rights or issuer coverage')
    r=dict(record)
    if not isinstance(r['market_cap_usd'],str):raise ValueError('Decimal string required')
    value=Decimal(r['market_cap_usd'])
    if not value.is_finite() or value<=0:raise ValueError('Positive finite issuer equity value required')
    if r['currency']!='USD' or r['method']!='provider_reported_issuer_equity' or r['issuer_scope']!='whole_issuer_all_classes':
        raise ValueError('Only reviewed direct USD whole-issuer capitalization supported')
    if not date.fromisoformat(r['as_of'])<=date.fromisoformat(r['verified_on'])<=date.today():raise ValueError('Invalid market cap date')
    if r['measured_at']:
        measured=datetime.fromisoformat(r['measured_at'])
        if measured.tzinfo is None or measured.astimezone(timezone.utc).date().isoformat()!=r['as_of'] or measured>datetime.now(timezone.utc):raise ValueError('Invalid measurement timestamp')
    url=urlsplit(r['source_url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password:raise ValueError('Invalid source URL')
    if any(not r[k].strip() for k in ('source_id','source_version','basis_evidence','access_evidence')):raise ValueError('Source and access evidence required')
    return r


def initialize_isolated(connection,expected_signature=None):
    if not connection.info.dbname.startswith(PREFIX):raise ValueError('Market cap requires owned isolation')
    from app.database.activate_earnings import digest,catalog
    with connection.transaction():
        objects=connection.execute("SELECT to_regclass('public.earnings_market_cap_snapshots'),to_regprocedure('public.earnings_market_cap_guard()')").fetchone()
        if any(objects):
            if all(objects) and expected_signature and digest(catalog(connection,True))==expected_signature:return 'already_initialized'
            raise ValueError('Partial/foreign market cap schema; reviewed signature required')
        connection.execute(SCHEMA.read_text(encoding='utf-8'))
    return 'created'


def import_records(connection,records,*,reviewed_path=None):
    if not connection.info.dbname.startswith(PREFIX):raise ValueError('Market cap import rejects normal database')
    prepared=[validate(r,reviewed_path) for r in records]
    with connection.transaction():
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        for r in prepared:
            fp=fingerprint(r)
            if connection.execute('SELECT 1 FROM earnings_market_cap_snapshots WHERE fingerprint=%s',(fp,)).fetchone():continue
            # A second manual review of the same measurement is not a new
            # source version, capture or timestamp. Conflicting content fails.
            prior=connection.execute('SELECT '+','.join(sorted(FIELDS))+' FROM earnings_market_cap_snapshots WHERE company_id=%s AND source_id=%s AND as_of=%s AND source_version=%s',
                (identity(r['cik']),r['source_id'],r['as_of'],r['source_version'])).fetchone()
            if prior:
                stored=dict(zip(sorted(FIELDS),prior))
                same=all(str(stored[k])==str(r[k]) for k in FIELDS-{'verified_on','market_cap_usd','measured_at','as_of','basis_evidence'})
                same=same and measurement_basis(stored['basis_evidence'])==measurement_basis(r['basis_evidence'])
                same=same and stored['market_cap_usd']==Decimal(r['market_cap_usd']) and str(stored['as_of'])==r['as_of']
                same=same and (stored['measured_at']==datetime.fromisoformat(r['measured_at']) if r['measured_at'] else stored['measured_at'] is None)
                if not same:raise ValueError('Conflicting market cap source version')
                continue
            columns=['snapshot_id','company_id']+sorted(FIELDS)+['fingerprint']
            from psycopg import sql
            connection.execute(sql.SQL('INSERT INTO earnings_market_cap_snapshots ({}) VALUES ({})').format(
                sql.SQL(',').join(map(sql.Identifier,columns)),sql.SQL(',').join(sql.Placeholder() for _ in columns)),
                [identity('market-cap:'+fp),identity(r['cik'])]+[r[k] for k in sorted(FIELDS)]+[fp])


def attach(connection,events):
    objects=connection.execute("SELECT to_regclass('public.earnings_market_cap_snapshots'),to_regprocedure('public.earnings_market_cap_guard()')").fetchone()
    if any(objects) and not all(objects):raise ValueError('Incomplete market cap store')
    latest={}
    if all(objects):
        with connection.cursor(row_factory=dict_row) as cursor:
            # A date-only observation is conservatively ordered before timed
            # observations of that day; verification time never beats as_of.
            cursor.execute('''SELECT DISTINCT ON (company_id) * FROM earnings_market_cap_snapshots
                WHERE as_of<=CURRENT_DATE AND verified_on<=CURRENT_DATE
                ORDER BY company_id,as_of DESC,measured_at DESC NULLS LAST,verified_on DESC,captured_at DESC,snapshot_id''')
            latest={str(r['company_id']):r for r in cursor.fetchall()}
    for event in events:
        r=latest.get(event['company_id'])
        if r and r['cik']!=event['cik']:raise ValueError('Market cap CIK mismatch')
        fresh=r is not None and is_fresh(r['as_of']) and access_is_current(r['basis_evidence'])
        event.update(market_cap_usd=str(r['market_cap_usd']) if fresh else None,
                     market_cap_as_of=str(r['as_of']) if fresh else None,
                     market_cap_source=r['source_url'] if fresh else None,
                     market_cap_status=('verified_snapshot' if fresh else 'stale' if is_fresh(r['as_of']) is False else 'unavailable') if r else 'unavailable' if all(objects) else 'not_activated',
                     market_cap_snapshot={k:str(v) if v is not None else None for k,v in r.items()} if r else None)
    from app.earnings_market_cap_cache import attach as attach_cache
    return attach_cache(events, utc_today())
