"""Explicit E2B activation, independent of the isolated-only initializers.

Prepare is read-only. Apply requires separate user approval of the complete
target/plan hash, unchanged artifacts, a fresh backup and full restore evidence.
Never imported by API/startup; never performs publisher HTTP.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg import sql
from psycopg.pq import TransactionStatus
from app import earnings_financials as financials
from app.database import activate_earnings as base
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[2]
TABLES = ('earnings_financial_documents','earnings_financial_observations')
ARTIFACTS = ('app/database/activate_earnings_financials.py',
             'app/database/earnings_financial_schema.sql',
             'app/database/activate_earnings.py','app/earnings.py','app/earnings_financials.py',
             'config/earnings_financial_manual.json',
             'docs/audits/equity-earnings-financial-activation-rollback-2026-11-03.md')
EXPECTED_E2A = dict(zip(base.TABLES,(3,3,6,6,5,12)))
EXPECTED_AFTER = {**EXPECTED_E2A,'earnings_periods':10,'earnings_events':10,
                  'earnings_financial_documents':6,'earnings_financial_observations':12}


def artifacts(): return {p:base.file_hash(ROOT/p) for p in ARTIFACTS}


def counts(connection, names):
    return {p:connection.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(p))).fetchone()[0] for p in names}


def table_snapshots(connection, names=None):
    """Exact ordered binary-COPY hashes, not approximate PostgreSQL statistics."""
    tables=connection.execute("SELECT c.relname,c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname").fetchall()
    result={}
    import hashlib
    for name,oid in tables:
        if names is not None and name not in names: continue
        keys=connection.execute('''SELECT a.attname FROM pg_index i CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ord)
            JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
            WHERE i.indrelid=%s AND i.indisprimary ORDER BY k.ord''',(oid,)).fetchall()
        order=sql.SQL(',').join(sql.Identifier(k[0]) for k in keys) if keys else sql.SQL('row_to_json(t)::text')
        checksum=hashlib.sha256()
        with connection.cursor() as cursor:
            with cursor.copy(sql.SQL('COPY (SELECT * FROM public.{} t ORDER BY {}) TO STDOUT (FORMAT binary)').format(sql.Identifier(name),order)) as stream:
                for block in stream: checksum.update(block)
        result[name]={'rows':counts(connection,[name])[name],'sha256':checksum.hexdigest()}
    return result


def e2a_rows(connection, added_periods=()):
    """Rows already present before E2B, excluding only the four planned additions."""
    result={}
    for name in base.TABLES:
        where=sql.SQL('')
        params=()
        if added_periods and name in ('earnings_periods','earnings_events'):
            where=sql.SQL(' WHERE NOT (period_id=ANY(%s::uuid[]))');params=(list(added_periods),)
        result[name]=[row[0] for row in connection.execute(sql.SQL('SELECT row_to_json(t)::text FROM public.{} t{} ORDER BY row_to_json(t)::text').format(sql.Identifier(name),where),params).fetchall()]
    return result


def reserved_check(state, reference, phase):
    expected=reference[phase]
    if (state['earnings_schema_signature']!=expected['earnings_schema_signature']
        or base.digest(state['existing_objects'])!=base.digest(expected['existing_objects'])):
        raise ValueError('Partial, foreign or incompatible Earnings schema; no automatic repair')


def check_backup(manifest, target):
    base.check_backup(manifest,target)
    evidence=manifest['restore_validation']
    path=Path(evidence['path'])
    if base.file_hash(path)!=evidence['sha256']:
        raise ValueError('Restore evidence hash changed')
    proof=json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('source_target')!=target or proof.get('backup_sha256')!=manifest['sha256']
        or proof.get('restore_exit_code')!=0 or proof.get('unvalidated_constraints')!=0
        or proof.get('source_snapshots')!=proof.get('restored_snapshots')
        or not proof.get('source_snapshots') or proof.get('schema_match') is not True
        or proof.get('owned_database_removed') is not True):
        raise ValueError('A successful complete restore with matching tables/schema is required')
    if proof['source_snapshots']!=manifest['source_snapshots']:
        raise ValueError('Backup and restore refer to different source snapshots')
    return proof


def seed():
    rows=json.loads(financials.DATA.read_text(encoding='utf-8'))
    for row in rows: financials.validate(row)
    approved=[('NVDA',2027,1,'81615','2.39'),('NVDA',2027,2,'96221','2.46'),
              ('AMZN',2026,2,'200606','5.75'),('AMZN',2026,3,'201944','1.89'),
              ('INTC',2026,2,'16128','-2.16'),('INTC',2026,3,'16513','0.60')]
    actual=[(r['ticker'],r['fiscal_year'],r['fiscal_quarter'],r['observations'][0]['source_value'],r['observations'][1]['source_value']) for r in rows]
    if actual!=approved: raise ValueError('Seed differs from the six approved quarterly reports')
    return rows


def prepare(connection, confirmed_target, backup, reference):
    state=base.inspect(connection)
    if base.target_label(state['target'])!=confirmed_target:
        raise ValueError('Explicit target differs from live database')
    reserved_check(state,reference,'e2a')
    proof=check_backup(backup,state['target'])
    if proof['source_earnings_signature']!=state['earnings_schema_signature'] or proof['source_macro_signature']!=state['macro_schema_signature']:
        raise ValueError('Backup no longer matches the live schema')
    rows=seed(); additions=[]
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        if base.target_identity(connection)!=state['target'] or base.digest(base.catalog(connection,True))!=state['earnings_schema_signature'] or base.digest(base.catalog(connection,False))!=state['macro_schema_signature']:
            raise ValueError('Target/schema changed during preparation')
        if counts(connection,base.TABLES)!=EXPECTED_E2A:
            raise ValueError('Unexpected E2A record counts')
        snapshots=table_snapshots(connection)
        if snapshots!=backup['source_snapshots']:
            raise ValueError('Data changed since backup; prepare a fresh reviewed plan')
        original=e2a_rows(connection)
        for r in rows:
            company=financials.identity(r['cik'])
            if not connection.execute('SELECT 1 FROM earnings_companies WHERE company_id=%s AND cik=%s AND ticker=%s',(company,r['cik'],r['ticker'])).fetchone():
                raise ValueError('Company identity conflict')
            period=financials.identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}")
            existing=connection.execute('SELECT period_label,period_end FROM earnings_periods WHERE period_id=%s',(period,)).fetchone()
            if existing and (existing[0],str(existing[1]))!=(r['period_label'],r['period_end']):
                raise ValueError('Existing fiscal period conflict')
            if not existing: additions.append({'period_id':period,'event_id':financials.identity(period+':earnings'),'ticker':r['ticker'],'label':r['period_label']})
        if len(additions)!=4: raise ValueError('Expected exactly four missing historical periods')
    return dict(version=1,prepared_at=datetime.now(timezone.utc).isoformat(),target=state['target'],target_label=confirmed_target,
                preflight=state,backup=backup,reference=reference,artifacts=artifacts(),source_snapshots=snapshots,
                original_e2a_rows=original,additions=additions,expected_counts=EXPECTED_AFTER,
                ddl_tables=list(TABLES),manual_documents=6,manual_observations=12,
                status='ready_for_explicit_user_approval_not_executed')


def verify_seed(connection, rows):
    """Reject extra/corrupt financial records on an idempotent repeat, without reactivation."""
    expected_docs=set();expected_obs=set()
    for row in rows:
        document={k:row[k] for k in row if k!='observations'}
        doc=financials.identity('financial-document:'+financials.fingerprint(document));expected_docs.add(doc)
        company=financials.identity(row['cik']);period=financials.identity(f"{row['cik']}:{row['fiscal_year']}:{row['fiscal_quarter']}")
        event=financials.identity(period+':earnings');d=row['document']
        stored=connection.execute('''SELECT company_id,period_id,event_id,cik,period_end,release_date,source_url,document_type,
            sec_accession,verified_on,evidence_method,source_version,availability_status,record_fingerprint
            FROM earnings_financial_documents WHERE document_id=%s''',(doc,)).fetchone()
        expected=(company,period,event,row['cik'],row['period_end'],row['release_date'],d['source_url'],d['document_type'],
                  d['sec_accession'],d['verified_on'],d['evidence_method'],d['source_version'],d['availability_status'],financials.fingerprint(document))
        if stored is None or tuple(str(v) if v is not None else None for v in stored)!=expected:
            raise ValueError('Stored financial document differs from approved facts')
        for metric in row['observations']:
            fp=financials.fingerprint({'document':doc,'metric':metric})
            obs=financials.identity('financial-observation:'+fp);expected_obs.add(obs)
            from decimal import Decimal
            stored=connection.execute('''SELECT document_id,event_id,period_id,company_id,metric,actual,currency,unit,
                source_value,source_unit,decimal_places,methodology,version,supersedes_id,correction_reason,record_fingerprint
                FROM earnings_financial_observations WHERE observation_id=%s''',(obs,)).fetchone()
            expected=(doc,event,period,company,metric['metric'],str(Decimal(metric['source_value'])*financials.SCALES[metric['source_unit']]),
                'USD',financials.METRICS[metric['metric']][0],metric['source_value'],metric['source_unit'],str(metric['decimal_places']),
                metric['methodology'],'1',None,None,fp)
            if stored is None or tuple(str(v) if v is not None else None for v in stored)!=expected:
                raise ValueError('Stored financial observation differs from approved facts')
    stored_docs={str(r[0]) for r in connection.execute('SELECT document_id FROM earnings_financial_documents')}
    stored_obs={str(r[0]) for r in connection.execute('SELECT observation_id FROM earnings_financial_observations')}
    if stored_docs!=expected_docs or stored_obs!=expected_obs:
        raise ValueError('Financial data differ from the approved seed; separate review required')


def apply(connection, plan, confirmed_target, confirmed_plan):
    """Do not call on the developer database until the user approves this exact plan."""
    if confirmed_target!=plan['target_label'] or confirmed_plan!=base.digest(plan):
        raise ValueError('Explicit target and complete approved plan hash required')
    if plan['version']!=1 or plan['artifacts']!=artifacts():
        raise ValueError('Frozen activation artifacts changed')
    check_backup(plan['backup'],plan['target'])
    rows=seed()
    state=base.inspect(connection)
    if state['target']!=plan['target']:
        raise ValueError('Database/cluster/OID/role differs from approved target')
    if state['macro_schema_signature']!=plan['preflight']['macro_schema_signature']:
        raise ValueError('Macro schema changed since approval')
    phase='e2b' if set(state['existing_tables'])==set(EXPECTED_AFTER) else 'e2a'
    reserved_check(state,plan['reference'],phase)
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ WRITE')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute("SET LOCAL lock_timeout TO '5s'")
        connection.execute("SET LOCAL statement_timeout TO '120s'")
        connection.execute('SELECT pg_advisory_xact_lock(726530019)')
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        if base.target_identity(connection)!=plan['target']:
            raise ValueError('Target identity changed')
        # Refuse an unapproved schema appearing between preflight and write transaction.
        if base.digest(base.catalog(connection,True))!=plan['reference'][phase]['earnings_schema_signature'] or base.digest(base.catalog(connection,False))!=plan['preflight']['macro_schema_signature']:
            raise ValueError('Schema changed before write transaction')
        macro_names=set(plan['source_snapshots'])-set(base.TABLES)
        macro_before=table_snapshots(connection,macro_names)
        if macro_before!={k:v for k,v in plan['source_snapshots'].items() if k in macro_names}:
            raise ValueError('Macro data changed since backup; new review required')
        added=[r['period_id'] for r in plan['additions']] if phase=='e2b' else []
        if e2a_rows(connection,added)!=plan['original_e2a_rows']:
            raise ValueError('Existing E2A data changed since approval')
        if phase=='e2a':
            if counts(connection,base.TABLES)!=EXPECTED_E2A: raise ValueError('Unexpected E2A counts')
            connection.execute(financials.SCHEMA.read_text(encoding='utf-8'))
        financials.import_records(connection,rows)
        if base.digest(base.catalog(connection,True))!=plan['reference']['e2b']['earnings_schema_signature'] or base.digest(base.catalog(connection,False))!=plan['preflight']['macro_schema_signature']:
            raise ValueError('Resulting schema differs from isolated reference')
        if counts(connection,EXPECTED_AFTER)!=EXPECTED_AFTER:
            raise ValueError('Unexpected activation counts')
        verify_seed(connection,rows)
        if e2a_rows(connection,[r['period_id'] for r in plan['additions']])!=plan['original_e2a_rows'] or table_snapshots(connection,macro_names)!=macro_before:
            raise ValueError('Existing E2A or macro data changed; rolling back everything')
        receipt={'outcome':'created' if phase=='e2a' else 'already_initialized','target':plan['target'],
                 'approved_plan':confirmed_plan,'counts':counts(connection,EXPECTED_AFTER),
                 'after_snapshots':table_snapshots(connection),'additions':plan['additions']}
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    dry=commands.add_parser('prepare');dry.add_argument('--target',required=True)
    dry.add_argument('--backup-manifest',type=Path,required=True)
    dry.add_argument('--schema-reference',type=Path,required=True);dry.add_argument('--out',type=Path,required=True)
    write=commands.add_parser('apply');write.add_argument('--plan',type=Path,required=True)
    write.add_argument('--confirm-target',required=True);write.add_argument('--confirm-plan',required=True)
    write.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        with get_independent_connection() as c:
            c.read_only=True
            plan=prepare(c,args.target,json.loads(args.backup_manifest.read_text(encoding='utf-8')),json.loads(args.schema_reference.read_text(encoding='utf-8')))
        with args.out.open('x',encoding='utf-8') as stream: json.dump(plan,stream,default=str,indent=2)
        print(json.dumps({'target':plan['target_label'],'plan_sha256':base.digest(plan),'mode':'read_only_prepare'}))
    else:
        plan=json.loads(args.plan.read_text(encoding='utf-8'))
        if args.receipt.exists(): raise ValueError('Receipt already exists; choose a new path')
        with get_independent_connection() as c: receipt=apply(c,plan,args.confirm_target,args.confirm_plan)
        with args.receipt.open('x',encoding='utf-8') as stream: json.dump(receipt,stream,default=str,indent=2)
        print(json.dumps({'outcome':receipt['outcome'],'approved_plan':receipt['approved_plan'],'counts':receipt['counts']}))


if __name__=='__main__': main()
