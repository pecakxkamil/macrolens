"""Explicit E2E activation: read-only prepare, separately approved atomic apply.

Never imported by API/startup. No HTTP or automatic post-COMMIT rollback.
Existing isolated initializer and importer guards remain unchanged.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg import sql
from app import earnings_history as reports
from app.earnings_previous import previous_quarter
from psycopg.types.json import Jsonb
from app.database import activate_earnings_reports as current
from app.database import activate_earnings as base
from app.database import activate_earnings_financials as financial
from app.database import activate_earnings_coverage as coverage
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[2]
TABLES = ('earnings_historical_reports',)
BEFORE = current.AFTER
AFTER = {**BEFORE, TABLES[0]:23}
ROLLBACK = 'docs/audits/equity-earnings-previous-activation-rollback-2026-11-04.md'
ARTIFACTS = tuple(dict.fromkeys((
    'app/database/activate_earnings_history.py', ROLLBACK,
    'app/database/earnings_history_schema.sql', 'app/earnings_history.py',
    'app/earnings_previous.py', 'app/earnings.py', 'config/earnings_previous_reviewed.json', *current.ARTIFACTS)))


def artifacts():
    return {p:base.file_hash(ROOT/p) for p in ARTIFACTS}


def seed():
    records=[reports.validate(r) for r in json.loads(reports.DATA.read_text(encoding='utf-8'))]
    count=lambda metric:sum(m['metric']==metric for r in records for m in r['observations'])
    if len(records)!=23 or len({(r['cik'],r['fiscal_year'],r['fiscal_quarter']) for r in records})!=23 or count('revenue')!=23 or count('reported_diluted_eps')!=22:
        raise ValueError('Frozen history requires 23 snapshots / 23 Revenue / 22 EPS')
    currents={r['cik']:r for r in current.seed() if r['document']['document_type']=='earnings_release'}
    for r in records:
        parent=currents[r['cik']]
        if (r['fiscal_year'],r['fiscal_quarter'])!=previous_quarter(parent['fiscal_year'],parent['fiscal_quarter']) or r['document_type']!='earnings_release' or r.get('correction_reason'):
            raise ValueError('Exact fiscal predecessor and original release required')
        metrics={m['metric'] for m in r['observations']}
        if metrics!=({'revenue'} if r['ticker']=='CRWD' else {'revenue','reported_diluted_eps'}):raise ValueError('CRWD EPS must remain absent')
    return records


def manifest(records):
    return {TABLES[0]:sorted([dict(document_id=reports.identity('historical:'+reports.fingerprint(r)),
        company_id=reports.identity(r['cik']),cik=r['cik'],fiscal_year=r['fiscal_year'],fiscal_quarter=r['fiscal_quarter'],
        version=1,supersedes_id=None,correction_reason=None,record_fingerprint=reports.fingerprint(r),payload=r) for r in records],key=lambda r:r['document_id'])}


def import_seed(connection,records):
    # Explicit approved activation path only. The normal importer stays guarded.
    for r in records:
        fp=reports.fingerprint(r)
        if connection.execute('SELECT 1 FROM earnings_historical_reports WHERE record_fingerprint=%s',(fp,)).fetchone():continue
        connection.execute('''INSERT INTO earnings_historical_reports(document_id,company_id,cik,fiscal_year,fiscal_quarter,version,supersedes_id,correction_reason,record_fingerprint,payload)
            VALUES(%s,%s,%s,%s,%s,1,NULL,NULL,%s,%s)''',
            (reports.identity('historical:'+fp),reports.identity(r['cik']),r['cik'],r['fiscal_year'],r['fiscal_quarter'],fp,Jsonb(r)))


def verify_seed(connection,expected):
    fields=list(expected[TABLES[0]][0])
    query=sql.SQL('SELECT {} FROM public.{} ORDER BY document_id').format(sql.SQL(',').join(map(sql.Identifier,fields)),sql.Identifier(TABLES[0]))
    actual=[]
    for row in connection.execute(query):
        d=dict(zip(fields,row));d['document_id']=str(d['document_id']);d['company_id']=str(d['company_id']);actual.append(d)
    if actual!=expected[TABLES[0]]:raise ValueError('History differs from exact approved manifest')


def check_reference(reference):
    old,new=reference['before']['catalog'],reference['after']['catalog']
    if set(old)!=set(new):raise ValueError('Reference catalogs differ')
    def added(kind,row):
        return row[0]=='earnings_history_guard' if kind=='functions' else any(row[0].startswith(t) for t in TABLES)
    if any(added(kind,row) for kind,rows in old.items() for row in rows):
        raise ValueError('Reference baseline already has report objects')
    filtered={k:[r for r in values if not added(k,r)] for k,values in new.items()}
    if (base.digest(filtered)!=base.digest(old)
        or {r[0] for r in new['relations'] if r[1]=='r'}!=set(BEFORE)|set(TABLES)
        or len([r for r in new['functions'] if added('functions',r)])!=1
        or len([r for r in new['triggers'] if added('triggers',r)])!=3):
        raise ValueError('Reference must add only the one reviewed history table and guards')


def phase(state, reference):
    for name in ('before','after'):
        r=reference[name]
        if (state['earnings_schema_signature']==base.digest(r['catalog'])
            and base.digest(state['existing_objects'])==base.digest(r['objects'])):
            return name
    raise ValueError('Partial or foreign report store/schema')


def prepare(connection, expected_target, backup, reference):
    state=base.inspect(connection)
    if state['target']!=expected_target:raise ValueError('Explicit identity differs from live database')
    check_reference(reference)
    if phase(state,reference)!='before':raise ValueError('E2E already activated; no fresh plan prepared')
    proof=financial.check_backup(backup,expected_target)
    if (proof['source_earnings_signature']!=state['earnings_schema_signature']
        or proof['source_macro_signature']!=state['macro_schema_signature']):
        raise ValueError('Backup schema differs from live schema')
    records=seed();expected=manifest(records)
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        if (base.target_identity(connection)!=expected_target
            or base.digest(base.catalog(connection,True))!=state['earnings_schema_signature']
            or base.digest(base.catalog(connection,False))!=state['macro_schema_signature']):
            raise ValueError('Identity/schema changed during preparation')
        snapshots=financial.table_snapshots(connection)
        if len(snapshots)!=23 or snapshots!=backup['source_snapshots'] or financial.counts(connection,BEFORE)!=BEFORE:
            raise ValueError('Data changed since backup or unexpected 23-table baseline')
        original=coverage.rows(connection)
        for r in records:
            stored=connection.execute('SELECT cik,ticker FROM earnings_companies WHERE company_id=%s',(reports.identity(r['cik']),)).fetchone()
            if stored!=(r['cik'],r['ticker']):raise ValueError('Existing issuer differs from history')
    return dict(version=1,prepared_at=datetime.now(timezone.utc).isoformat(),ready_for_apply=True,
        status='awaiting_explicit_approval_not_executed',target=expected_target,target_label=base.target_label(expected_target),
        artifacts=artifacts(),backup=backup,reference=reference,source_snapshots=snapshots,
        original_rows=original,seed_manifest=expected,expected_counts=AFTER,
        macro_signature=state['macro_schema_signature'],ddl_tables=list(TABLES))


def apply(connection, plan, confirmed_target, confirmed_plan):
    if confirmed_target!=plan['target_label'] or confirmed_plan!=base.digest(plan):
        raise ValueError('Explicit target and full approved plan hash required')
    if plan['version']!=1 or plan.get('ready_for_apply') is not True or plan['artifacts']!=artifacts():
        raise ValueError('Frozen artifacts or plan readiness changed')
    financial.check_backup(plan['backup'],plan['target'])
    check_reference(plan['reference'])
    records=seed();expected=manifest(records)
    if expected!=plan['seed_manifest'] or plan['expected_counts']!=AFTER:
        raise ValueError('Seed manifest differs from approved plan')
    state=base.inspect(connection)
    if state['target']!=plan['target'] or state['macro_schema_signature']!=plan['macro_signature']:
        raise ValueError('Identity or macro schema differs from approved plan')
    current=phase(state,plan['reference'])
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ WRITE')
        if connection.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend'").fetchone()[0]:
            raise ValueError('Maintenance window requires no other database clients')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute("SET LOCAL lock_timeout TO '5s'")
        connection.execute("SET LOCAL statement_timeout TO '120s'")
        connection.execute('SELECT pg_advisory_xact_lock(726530019)')
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        if (base.target_identity(connection)!=plan['target']
            or base.digest(base.catalog(connection,True))!=base.digest(plan['reference'][current]['catalog'])
            or base.digest(base.catalog(connection,False))!=plan['macro_signature']):
            raise ValueError('Identity/schema changed before write transaction')
        before=financial.table_snapshots(connection)
        if ({t:s for t,s in before.items() if t not in TABLES}!=plan['source_snapshots']
            or coverage.rows(connection)!=plan['original_rows']):
            raise ValueError('Original E2A-E2D or macro data changed since approval')
        if current=='before':
            if before!=plan['source_snapshots']:raise ValueError('Unexpected baseline tables')
            connection.execute(reports.SCHEMA.read_text(encoding='utf-8'))
        else:
            if set(before)!=set(plan['source_snapshots'])|set(TABLES):raise ValueError('Unexpected report tables')
            verify_seed(connection,expected)
        import_seed(connection,records)
        verify_seed(connection,expected)
        after=financial.table_snapshots(connection)
        if (set(after)!=set(plan['source_snapshots'])|set(TABLES)
            or {t:s for t,s in after.items() if t not in TABLES}!=plan['source_snapshots']
            or coverage.rows(connection)!=plan['original_rows']
            or financial.counts(connection,AFTER)!=AFTER
            or base.digest(base.catalog(connection,True))!=base.digest(plan['reference']['after']['catalog'])
            or base.digest(base.catalog(connection,False))!=plan['macro_signature']
            or (current=='after' and after!=before)):
            raise ValueError('Result differs from approved schema/facts or original data; rollback')
        receipt=dict(outcome='created' if current=='before' else 'already_initialized',target=plan['target'],
            approved_plan=confirmed_plan,counts=AFTER,after_snapshots=after,seed_manifest=expected)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    dry=commands.add_parser('prepare')
    for name in ('identity','backup-manifest','schema-reference','out'):dry.add_argument('--'+name,type=Path,required=True)
    write=commands.add_parser('apply');write.add_argument('--plan',type=Path,required=True)
    write.add_argument('--confirm-target',required=True);write.add_argument('--confirm-plan',required=True)
    write.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args();destination=args.out if args.command=='prepare' else args.receipt
    if destination.exists():raise ValueError('Output exists; refuse overwrite')
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    with get_independent_connection() as c:
        if args.command=='prepare':
            c.read_only=True;result=prepare(c,read(args.identity),read(args.backup_manifest),read(args.schema_reference))
        else:result=apply(c,read(args.plan),args.confirm_target,args.confirm_plan)
    with destination.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,default=str)
    print(json.dumps(dict(mode=args.command,plan_sha256=base.digest(result) if args.command=='prepare' else args.confirm_plan)))


if __name__=='__main__':main()
