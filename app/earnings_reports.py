"""E2D manual official report evidence and original-currency actuals. No HTTP.

Separate append-only tables leave all E2B rows/allowlists unchanged. Only the
isolated CLI can initialize/import; GET tolerates an absent E2D store.
"""
import argparse
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from app import earnings_coverage as coverage
from app.earnings import identity
from app.earnings_financials import fingerprint

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'config/earnings_reports_manual.json'
SCHEMA = ROOT / 'app/database/earnings_report_schema.sql'
TABLES = ('earnings_report_documents', 'earnings_report_observations')
PREFIX = 'macrolens_earnings_e2b_e2c_e2d_'
SCALES = {k:Decimal(v) for k,v in [('units',1),('thousands',1000),('millions',1000000),('billions',1000000000),('per_share',1)]}
EXTRA_HOSTS = {'AAPL':{'www.apple.com'}, 'MSFT':{'www.microsoft.com'},
               'GOOGL':{'s206.q4cdn.com'}, 'TSLA':{'assets-ir.tesla.com'},
               'ADBE':{'www.adobe.com'}, 'ASML':{'www.sec.gov'}, 'NOW':{'newsroom.servicenow.com'}}


def validate(record):
    r=json.loads(json.dumps(record))
    if set(r)-{'cik','ticker','fiscal_year','fiscal_quarter','period_label','period_end','document','observations','correction_reason'}:
        raise ValueError('Unsupported report fields; forecasts are forbidden')
    ledger=json.loads(coverage.DATA.read_text(encoding='utf-8'))
    known=next((x for x in ledger if (x['cik'],x['fiscal_year'],x['fiscal_quarter'])==(r['cik'],r['fiscal_year'],r['fiscal_quarter'])),None)
    if not known or r['ticker']!=known['ticker'] or r['period_label']!=known['period_label']:
        raise ValueError('Unreviewed issuer/fiscal quarter/label')
    if type(r['fiscal_year']) is not int or type(r['fiscal_quarter']) is not int:
        raise ValueError('Fiscal values must be integers')
    if known['period_end'] and r['period_end']!=known['period_end']:
        raise ValueError('Period end conflicts with reviewed E2C period')
    reviewed=next(x for x in json.loads(DATA.read_text(encoding='utf-8')) if x['cik']==r['cik'] and x['fiscal_year']==r['fiscal_year'] and x['fiscal_quarter']==r['fiscal_quarter'])
    if r['period_end']!=reviewed['period_end']:
        raise ValueError('Unreviewed financial period end')
    d=r['document']
    if set(d)!={'document_type','source_url','linked_from','release_date','verified_on','verification_method','source_version','facts','reporting_standard','reporting_currency','eps_share_basis'}:
        raise ValueError('Explicit reviewed documentary provenance required')
    if any(d[k]!=reviewed['document'][k] for k in ('document_type','source_url','linked_from','release_date')):
        raise ValueError('Document issuer/period/publication evidence differs from reviewed source')
    company=coverage.registry()[r['cik']]
    parsed=urlsplit(d['source_url'])
    if parsed.scheme!='https' or parsed.hostname not in set(company['official_hosts'])|EXTRA_HOSTS.get(r['ticker'],set()) or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.fragment:
        raise ValueError('Unofficial report URL')
    if parsed.hostname=='www.sec.gov' and not parsed.path.startswith('/Archives/edgar/data/'+str(int(r['cik']))+'/'):
        raise ValueError('SEC URL identifies another issuer')
    if parsed.hostname=='s206.q4cdn.com' and not parsed.path.startswith('/479360582/'):
        raise ValueError('Unreviewed publisher CDN account')
    if d['linked_from']:
        link=urlsplit(d['linked_from'])
        if link.scheme!='https' or link.hostname not in set(company['official_hosts'])|EXTRA_HOSTS.get(r['ticker'],set()) or link.username or link.password:
            raise ValueError('Unreviewed official document link')
    verified=date.fromisoformat(d['verified_on'])
    if verified>date.today() or d['verification_method']!='manual_official_report_review' or not d['source_version'].strip() or not d['facts'].strip():
        raise ValueError('Manual official-source verification required')
    if d['document_type']=='earnings_release':
        released=date.fromisoformat(d['release_date'])
        if released>verified or (r['period_end'] and date.fromisoformat(r['period_end'])>released):
            raise ValueError('Future release or wrong period end')
        if any(d[k] is not None and d[k]!=reviewed['document'][k] for k in ('reporting_standard','reporting_currency','eps_share_basis')):
            raise ValueError('Reporting basis differs from reviewed issuer disclosure')
        if r['observations'] and (d['reporting_standard'] not in ('US_GAAP','IFRS') or d['reporting_currency'] not in ('USD','EUR','TWD')):
            raise ValueError('Actual requires an explicit reporting basis/currency')
        if any(m.get('metric')=='reported_diluted_eps' for m in r['observations']) and d['eps_share_basis'] not in ('common_share','ordinary_share','ADR'):
            raise ValueError('EPS requires a verified share unit')
    elif d['document_type']!='earnings_date_announcement' or d['release_date'] is not None or r['observations']:
        raise ValueError('Announcement cannot prove publication or carry Actual')
    if not isinstance(r['observations'],list) or len(r['observations'])>2:
        raise ValueError('At most two separately verified metrics required')
    seen=set()
    for m in r['observations']:
        if set(m)-{'metric','source_value','source_unit','currency','decimal_places','reporting_standard','share_basis','methodology','correction_reason'}:
            raise ValueError('Unsupported metric fields')
        metric=m['metric']
        if metric not in ('revenue','reported_diluted_eps') or metric in seen:
            raise ValueError('Only consolidated revenue / reported diluted EPS')
        seen.add(metric)
        expected_unit=set(SCALES)-{'per_share'} if metric=='revenue' else {'per_share'}
        if (m['currency']!=d['reporting_currency'] or m['reporting_standard']!=d['reporting_standard']
            or m['source_unit'] not in expected_unit
            or m['share_basis']!=('not_applicable' if metric=='revenue' else d['eps_share_basis'])
            or m['methodology']!=('consolidated_revenue' if metric=='revenue' else 'reported_diluted_total_eps')):
            raise ValueError('Currency/standard/share basis/diluted methodology conflict')
        reviewed_metric=next((x for x in reviewed['observations'] if x['metric']==metric),None)
        if not reviewed_metric or m['source_unit']!=reviewed_metric['source_unit']:
            raise ValueError('Source unit differs from reviewed financial statement')
        if type(m['decimal_places']) is not int or not 0<=m['decimal_places']<=6 or not isinstance(m['source_value'],str):
            raise ValueError('Explicit decimal string/precision required')
        try:v=Decimal(m['source_value'])
        except (ValueError,InvalidOperation):raise ValueError('Invalid decimal')
        if not v.is_finite() or abs(v)>Decimal('1e16') or v.as_tuple().exponent < -m['decimal_places'] or (metric=='revenue' and v<0):
            raise ValueError('Invalid value/precision')
        if 'correction_reason' in m and not m['correction_reason'].strip():raise ValueError('Empty correction reason')
    if 'correction_reason' in r and not r['correction_reason'].strip():raise ValueError('Empty correction reason')
    return r


def initialize_isolated(connection, expected_signature=None):
    if not connection.info.dbname.startswith(PREFIX):raise ValueError('E2D requires an owned isolated database')
    from app.database.activate_earnings import digest,catalog
    with connection.transaction():
        objects=connection.execute("SELECT to_regclass('public.earnings_report_documents'),to_regclass('public.earnings_report_observations'),to_regprocedure('public.earnings_report_guard()')").fetchone()
        if any(objects):
            if all(objects) and expected_signature and digest(catalog(connection,True))==expected_signature:return 'already_initialized'
            raise ValueError('Partial/foreign E2D schema; matching reviewed signature required')
        connection.execute(SCHEMA.read_text(encoding='utf-8'))
        return 'created'


def import_records(connection, records):
    prepared=[validate(r) for r in records]
    if len({(r['cik'],r['fiscal_year'],r['fiscal_quarter']) for r in prepared})!=len(prepared):
        raise ValueError('Duplicate issuer/period in batch')
    with connection.transaction():
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        for r in prepared:
            company=identity(r['cik']);period=identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}");event=identity(period+':earnings')
            stored=connection.execute('''SELECT c.cik,p.period_label,p.period_end FROM earnings_events e
                JOIN earnings_periods p USING(period_id,company_id) JOIN earnings_companies c USING(company_id)
                WHERE e.event_id=%s AND e.period_id=%s AND e.company_id=%s''',(event,period,company)).fetchone()
            if not stored or stored[0]!=r['cik'] or stored[1]!=r['period_label'] or (stored[2] is not None and str(stored[2])!=r['period_end']):
                raise ValueError('Existing issuer/event/period required; no E2C mutations')
            metadata={k:v for k,v in r.items() if k!='observations'};fp=fingerprint(metadata);doc=identity('report-document:'+fp);d=r['document']
            if not connection.execute('SELECT 1 FROM earnings_report_documents WHERE document_id=%s',(doc,)).fetchone():
                prior=connection.execute('SELECT document_id,version FROM earnings_report_documents WHERE event_id=%s ORDER BY version DESC LIMIT 1',(event,)).fetchone()
                if bool(prior)!=bool(r.get('correction_reason')):raise ValueError('Document revision requires explicit predecessor/correction reason')
                connection.execute('''INSERT INTO earnings_report_documents
                    (document_id,event_id,period_id,company_id,cik,period_end,document_type,release_date,source_url,linked_from,verified_on,
                    verification_method,source_version,facts,reporting_standard,reporting_currency,eps_share_basis,version,supersedes_id,correction_reason,record_fingerprint)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (doc,event,period,company,r['cik'],r['period_end'],d['document_type'],d['release_date'],d['source_url'],d['linked_from'],d['verified_on'],
                     d['verification_method'],d['source_version'],d['facts'],d['reporting_standard'],d['reporting_currency'],d['eps_share_basis'],prior[1]+1 if prior else 1,prior[0] if prior else None,r.get('correction_reason'),fp))
            for m in r['observations']:
                fp=fingerprint({'document':doc,'metric':m});obs=identity('report-observation:'+fp)
                if connection.execute('SELECT 1 FROM earnings_report_observations WHERE observation_id=%s',(obs,)).fetchone():continue
                prior=connection.execute('SELECT observation_id,version FROM earnings_report_observations WHERE event_id=%s AND metric=%s ORDER BY version DESC LIMIT 1',(event,m['metric'])).fetchone()
                if bool(prior)!=bool(m.get('correction_reason')):raise ValueError('Metric revision requires explicit correction reason')
                unit=m['currency']+('/share' if m['metric']=='reported_diluted_eps' else '')
                connection.execute('''INSERT INTO earnings_report_observations
                    (observation_id,document_id,event_id,period_id,company_id,metric,actual,source_value,currency,source_unit,unit,decimal_places,
                    reporting_standard,share_basis,methodology,version,supersedes_id,correction_reason,record_fingerprint)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (obs,doc,event,period,company,m['metric'],Decimal(m['source_value'])*SCALES[m['source_unit']],Decimal(m['source_value']),m['currency'],m['source_unit'],unit,
                     m['decimal_places'],m['reporting_standard'],m['share_basis'],m['methodology'],prior[1]+1 if prior else 1,prior[0] if prior else None,m.get('correction_reason'),fp))


def publication_state(event, documents, now=None):
    now=now or datetime.now(timezone.utc)
    published=[d for d in documents if d['document_type']=='earnings_release']
    revenue=event.get('revenue_actual');eps=event.get('reported_eps_actual')
    if eps is None:eps=event.get('gaap_diluted_eps_actual')
    if published or event.get('financial_publication_status')=='published':
        missing=[k for k,v in [('revenue',revenue),('reported_diluted_eps',eps)] if v is None]
        state='published_complete' if not missing else 'published_pending' if len(missing)==2 else 'published_partial'
        return dict(code=state,reason='verified_official_release',missing_metrics=missing,evidence=published)
    release=event['release'];call=event['call']
    anchor=release if release['date_status'] not in ('unknown','cancelled') else call
    day=anchor.get('source_local_date')
    if not day or anchor['date_status'] in ('unknown','cancelled'):
        return dict(code='unconfirmed',reason='no_confirmed_release_date',missing_metrics=['revenue','reported_diluted_eps'],evidence=[])
    # Exact RELEASE time can establish overdue; call and approximate windows cannot.
    instant=release.get('scheduled_at_utc') if release.get('precision')=='exact' else None
    overdue=datetime.fromisoformat(instant)<now if instant else date.fromisoformat(day)<now.astimezone(ZoneInfo(anchor.get('source_timezone') or 'America/New_York')).date()
    return dict(code='date_passed_unconfirmed' if overdue else 'scheduled',reason='no_verified_release_document' if overdue else 'official_date_evidence_only',
                missing_metrics=['revenue','reported_diluted_eps'],evidence=[])


def attach(connection, events, now=None):
    available=connection.execute("SELECT to_regclass('public.earnings_report_documents'),to_regclass('public.earnings_report_observations')").fetchone()
    if any(available) and not all(available):raise ValueError('Incomplete report store; explicit recovery required')
    docs=[];observations=[]
    if all(available):
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute('SELECT * FROM earnings_report_documents ORDER BY event_id,version');docs=cursor.fetchall()
            cursor.execute('''SELECT o.*,d.source_url,d.document_type,d.verified_on,d.verification_method AS evidence_method,d.source_version,
                d.release_date,d.period_end,d.facts FROM earnings_report_observations o
                JOIN earnings_report_documents d USING(document_id,event_id,period_id,company_id) ORDER BY o.event_id,o.metric,o.version''')
            observations=cursor.fetchall()
    for e in events:
        document_history=[{k:str(v) if v is not None else None for k,v in d.items()} for d in docs if 'earnings:'+str(d['event_id'])==e['event_id']]
        history=[{k:str(v) if v is not None else None for k,v in r.items()} for r in observations if 'earnings:'+str(r['event_id'])==e['event_id']]
        current={r['metric']:r for r in history}
        e['reported_eps_actual']=e.get('gaap_diluted_eps_actual')
        if document_history:
            # Complete evidence snapshot: superseded-document metrics cannot silently survive a new report review.
            latest=document_history[-1]
            current={k:v for k,v in current.items() if v['document_id']==latest['document_id']}
            e['revenue_actual']=current.get('revenue')
            e['reported_eps_actual']=current.get('reported_diluted_eps')
            eps=e['reported_eps_actual']
            e['gaap_diluted_eps_actual']=eps if eps and eps['reporting_standard']=='US_GAAP' else None
            e['financial_release_date']=next((d['release_date'] for d in document_history if d['document_type']=='earnings_release'),None)
            e['financial_publication_status']='published' if any(d['document_type']=='earnings_release' for d in document_history) else 'unconfirmed'
            e['financial_data_status']='complete' if len(current)==2 else 'partial' if current else 'unavailable'
            e['financial_history']+=history
        e['report_store_status']='available' if all(available) else 'not_activated'
        e['report_documents']=document_history
        e['publication_state']=publication_state(e,document_history,now)
    return events


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=DATA)
    args=parser.parse_args()
    from app.database.connection import get_independent_connection
    with get_independent_connection() as c:
        if not c.info.dbname.startswith(PREFIX):raise ValueError('E2D CLI rejects normal database')
        with c.transaction():
            initialize_isolated(c)
            import_records(c,json.loads(args.input.read_text(encoding='utf-8')))


if __name__=='__main__':main()
