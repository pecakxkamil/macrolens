"""Explicit E2D activation: read-only prepare, separately approved atomic apply.

Never imported by API/startup. No HTTP or automatic post-COMMIT rollback.
Existing isolated initializer and importer guards remain unchanged.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg import sql
from app import earnings_reports as reports
from app.database import activate_earnings as base
from app.database import activate_earnings_financials as financial
from app.database import activate_earnings_coverage as coverage
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[2]
TABLES = reports.TABLES
BEFORE = coverage.AFTER
AFTER = {**BEFORE, TABLES[0]:27, TABLES[1]:46}
ROLLBACK = 'docs/audits/equity-earnings-report-activation-rollback-2026-11-04.md'
ARTIFACTS = tuple(dict.fromkeys((
    'app/database/activate_earnings_reports.py', ROLLBACK,
    'app/database/earnings_report_schema.sql', 'app/earnings_reports.py',
    'config/earnings_reports_manual.json', *coverage.ARTIFACTS)))


def artifacts():
    return {p:base.file_hash(ROOT/p) for p in ARTIFACTS}


def seed():
    rows=json.loads(reports.DATA.read_text(encoding='utf-8'))
    checked=[reports.validate(r) for r in rows]
    keys=lambda records:{(r['cik'],r['fiscal_year'],r['fiscal_quarter']) for r in records}
    announcements={r['ticker'] for r in checked if r['document']['document_type']=='earnings_date_announcement'}
    releases=[r for r in checked if r['document']['document_type']=='earnings_release']
    if (len(checked)!=27 or len(keys(checked))!=27 or keys(checked)!=keys(coverage.seed())
        or len(releases)!=23 or announcements!={'ARM','QCOM','PANW','SNOW'}
        or any({m['metric'] for m in r['observations']}!={'revenue','reported_diluted_eps'} for r in releases)
        or sum(len(r['observations']) for r in checked)!=46
        or any(r.get('correction_reason') or any(m.get('correction_reason') for m in r['observations']) for r in checked)):
        raise ValueError('Seed differs from the frozen 27 documents / 23 pairs / four announcements')
    return checked


def manifest(records):
    """All deterministic stored fields; timestamps are checked by full snapshots."""
    documents=[];observations=[]
    for r in records:
        company=reports.identity(r['cik'])
        period=reports.identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}")
        event=reports.identity(period+':earnings')
        metadata={k:v for k,v in r.items() if k!='observations'}
        fingerprint=reports.fingerprint(metadata);doc=reports.identity('report-document:'+fingerprint)
        common=dict(event_id=event,period_id=period,company_id=company)
        documents.append(dict(document_id=doc,**common,cik=r['cik'],period_end=r['period_end'],
                              **r['document'],version='1',supersedes_id=None,correction_reason=None,record_fingerprint=fingerprint))
        for m in r['observations']:
            fp=reports.fingerprint({'document':doc,'metric':m})
            observations.append(dict(observation_id=reports.identity('report-observation:'+fp),document_id=doc,**common,
                **m,actual=str(reports.Decimal(m['source_value'])*reports.SCALES[m['source_unit']]),
                unit=m['currency']+('/share' if m['metric']=='reported_diluted_eps' else ''),
                version='1',supersedes_id=None,correction_reason=None,record_fingerprint=fp))
    normalize=lambda row:{k:str(v) if v is not None else None for k,v in row.items()}
    return {TABLES[0]:sorted([normalize(d) for d in documents],key=lambda d:d['document_id']),
            TABLES[1]:sorted([normalize(o) for o in observations],key=lambda o:o['observation_id'])}


def verify_seed(connection, expected):
    for table in TABLES:
        fields=list(expected[table][0]);pk=fields[0]
        query=sql.SQL('SELECT {} FROM public.{} ORDER BY {}').format(
            sql.SQL(',').join(map(sql.Identifier,fields)),sql.Identifier(table),sql.Identifier(pk))
        actual=[dict(zip(fields,[str(v) if v is not None else None for v in row])) for row in connection.execute(query)]
        if actual!=expected[table]:
            raise ValueError('Report documents/metrics differ from the exact approved manifest')


def check_reference(reference):
    old,new=reference['before']['catalog'],reference['after']['catalog']
    if set(old)!=set(new):raise ValueError('Reference catalogs differ')
    def added(kind,row):
        return row[0]=='earnings_report_guard' if kind=='functions' else any(row[0].startswith(t) for t in TABLES)
    if any(added(kind,row) for kind,rows in old.items() for row in rows):
        raise ValueError('Reference baseline already has report objects')
    filtered={k:[r for r in values if not added(k,r)] for k,values in new.items()}
    if (base.digest(filtered)!=base.digest(old)
        or {r[0] for r in new['relations'] if r[1]=='r'}!=set(BEFORE)|set(TABLES)
        or len([r for r in new['functions'] if added('functions',r)])!=1
        or len([r for r in new['triggers'] if added('triggers',r)])!=4):
        raise ValueError('Reference must add only the two reviewed report tables and guards')


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
    if phase(state,reference)!='before':raise ValueError('E2D already activated; no fresh plan prepared')
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
        if len(snapshots)!=21 or snapshots!=backup['source_snapshots'] or financial.counts(connection,BEFORE)!=BEFORE:
            raise ValueError('Data changed since backup or unexpected 21-table baseline')
        original=coverage.rows(connection)
        for r in records:
            company=reports.identity(r['cik']);period=reports.identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}")
            event=reports.identity(period+':earnings')
            stored=connection.execute('''SELECT c.cik,c.ticker,p.period_label,p.period_end FROM earnings_events e
                JOIN earnings_periods p USING(period_id,company_id) JOIN earnings_companies c USING(company_id)
                WHERE e.event_id=%s AND e.period_id=%s AND e.company_id=%s''',(event,period,company)).fetchone()
            if (not stored or stored[:3]!=(r['cik'],r['ticker'],r['period_label'])
                or (stored[3] is not None and str(stored[3])!=r['period_end'])):
                raise ValueError('Existing issuer/event/fiscal period conflicts with report')
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
            raise ValueError('Original E2A/E2B/E2C or macro data changed since approval')
        if current=='before':
            if before!=plan['source_snapshots']:raise ValueError('Unexpected baseline tables')
            connection.execute(reports.SCHEMA.read_text(encoding='utf-8'))
        else:
            if set(before)!=set(plan['source_snapshots'])|set(TABLES):raise ValueError('Unexpected report tables')
            verify_seed(connection,expected)
        reports.import_records(connection,records)
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
