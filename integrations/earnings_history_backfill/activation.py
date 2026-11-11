"""Controlled extension of the existing append-only E2E store, never startup.

The private importer instance binds an additional reviewed ledger without
changing the live app/config or any active F1/monitor dependency.
"""
import argparse
import importlib.util
import json
from pathlib import Path
from psycopg import sql
from app import earnings_history as history,earnings,earnings_previous
from app.database import activate_earnings_history as legacy
from app.database import activate_earnings as base,activate_earnings_financials as financial,activate_forecast_f1 as f1
from app.database import forecast_f1_authorization_v2 as authorization
from app.database.connection import get_independent_connection

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
LEDGER=HERE/'reviewed.json'
TABLE='earnings_historical_reports'
CONDITIONS=dict(version=1,write_tables=[TABLE],insert_reports=7,insert_metrics=13,ddl=False,
    changes_to_existing_rows=False,advisory=726530020,lock_timeout='5s',statement_timeout='120s',
    transaction='READ COMMITTED',table_locks='SHARE on all existing Earnings tables',
    post_commit='independent verification; no automatic restore or rollback')


def artifacts():
    own={str(p.relative_to(ROOT)).replace('\\','/'):base.file_hash(p) for p in sorted(HERE.glob('*')) if p.is_file() and p.suffix in ('.py','.json')}
    return dict(backend=authorization.artifacts(),operation=own)


def records():
    # A separate module object, no assignment to app.earnings_history.DATA.
    spec=importlib.util.spec_from_file_location('reviewed_e2e_backfill',history.__file__)
    private=importlib.util.module_from_spec(spec);spec.loader.exec_module(private);private.DATA=LEDGER
    raw=json.loads(LEDGER.read_text(encoding='utf-8'))
    prepared=[private.validate(row) for row in raw]
    expected={('ARM',2027,1),('QCOM',2026,3),('PANW',2026,4),('SNOW',2027,2),('NVDA',2026,4),('AMZN',2026,1),('INTC',2026,1)}
    if len(prepared)!=7 or {(r['ticker'],r['fiscal_year'],r['fiscal_quarter']) for r in prepared}!=expected:raise ValueError('Exact seven reviewed predecessors required')
    for r in prepared:
        if r['document_type']!='earnings_release' or r['reporting_standard']!='US_GAAP' or r['currency']!='USD' or r.get('correction_reason'):raise ValueError('Unreviewed report basis/revision')
        required={'revenue'} if r['ticker']=='INTC' else {'revenue','reported_diluted_eps'}
        if {m['metric'] for m in r['observations']}!=required or len(r['observations'])!=len(required):raise ValueError('Exact reviewed metrics required')
        for m in r['observations']:
            if m['currency']!='USD' or m['reporting_standard']!='US_GAAP' or m['methodology']!=('consolidated_revenue' if m['metric']=='revenue' else 'reported_diluted_total_eps'):raise ValueError('Invalid financial basis')
            if m['share_basis']!=('not_applicable' if m['metric']=='revenue' else 'ordinary_share' if r['ticker']=='ARM' else 'common_share'):raise ValueError('ADR or incompatible shares')
    return prepared


def tables(c):
    return tuple(r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND left(tablename,9)='earnings_' ORDER BY tablename").fetchall())


def baseline(c):
    return dict(earnings=financial.table_snapshots(c,tables(c)),forecasts=financial.table_snapshots(c,('forecast_vintages','forecast_freezes','forecast_refresh_checks')),
        schema=f1.schema_state(c),references=f1.reference_data(c))


def prepare(c,expected_target,backup):
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if base.target_identity(c)!=expected_target or not 170000<=c.info.server_version<180000:raise ValueError('Exact target/PG17 required')
        rows=records();events=earnings.load_events(c);state=baseline(c)
        if TABLE not in state['earnings']:raise ValueError('Existing E2E store required; no DDL')
        for r in rows:
            company=c.execute('SELECT company_id::text,ticker FROM earnings_companies WHERE cik=%s',(r['cik'],)).fetchone()
            if company!=(str(history.identity(r['cik'])),r['ticker']):raise ValueError('Issuer identity mismatch')
            parents=[e for e in events if e['cik']==r['cik'] and earnings_previous.previous_quarter(e['fiscal_year'],e['fiscal_quarter'])==(r['fiscal_year'],r['fiscal_quarter'])]
            if len(parents)!=1 or any(p.get('previous_eps_actual') is not None or p.get('previous_revenue_actual') is not None for p in parents):raise ValueError('Only missing exact predecessors may be backfilled')
            if c.execute('SELECT 1 FROM earnings_historical_reports WHERE cik=%s AND fiscal_year=%s AND fiscal_quarter=%s',(r['cik'],r['fiscal_year'],r['fiscal_quarter'])).fetchone():raise ValueError('Historical period already present; no revision')
    plan=dict(version=1,ready_for_apply=True,target=expected_target,target_label=base.target_label(expected_target),conditions=CONDITIONS,
        artifacts=artifacts(),ledger=rows,ledger_sha256=base.file_hash(LEDGER),baseline=state,expected=legacy.manifest(rows)[TABLE])
    backup_check(backup,plan)
    return plan


def frozen(plan):
    if set(plan)!={'version','ready_for_apply','target','target_label','conditions','artifacts','ledger','ledger_sha256','baseline','expected'} or plan['version']!=1 or plan['ready_for_apply'] is not True or plan['conditions']!=CONDITIONS:raise ValueError('Invalid reviewed backfill plan')
    if plan['artifacts']!=artifacts() or plan['ledger']!=records() or plan['ledger_sha256']!=base.file_hash(LEDGER) or plan['expected']!=legacy.manifest(records())[TABLE]:raise ValueError('Frozen backfill artifacts/ledger changed')
    if plan['target_label']!=base.target_label(plan['target']):raise ValueError('Invalid target label')


def backup_check(backup,plan):
    financial.check_backup(backup,plan['target'])
    old={**plan['baseline']['earnings'],**plan['baseline']['forecasts']}
    if any(backup['source_snapshots'].get(t)!=s for t,s in old.items()):raise ValueError('Backup Earnings/Forecast baseline differs')


def live(c,plan):
    if base.target_identity(c)!=plan['target'] or not 170000<=c.info.server_version<180000:raise ValueError('Wrong PostgreSQL target')
    if f1.schema_state(c)!=plan['baseline']['schema'] or f1.reference_data(c)!=plan['baseline']['references']:raise ValueError('Schema/references changed')


def appended(c,plan):
    fields=list(plan['expected'][0]);result=[]
    for expected in plan['expected']:
        row=c.execute(sql.SQL('SELECT {} FROM earnings_historical_reports WHERE document_id=%s').format(sql.SQL(',').join(map(sql.Identifier,fields))),(expected['document_id'],)).fetchone()
        if row is None:return False
        item=dict(zip(fields,row));item['document_id']=str(item['document_id']);item['company_id']=str(item['company_id']);result.append(item)
    if result!=plan['expected']:raise ValueError('Conflicting imported history')
    return True


def preserved(c,plan):
    old=plan['baseline'];names=[t for t in old['earnings'] if t!=TABLE]
    if financial.table_snapshots(c,names)!={t:old['earnings'][t] for t in names}:raise ValueError('Existing Earnings data changed')
    if financial.table_snapshots(c,old['forecasts'])!=old['forecasts']:raise ValueError('Forecast data changed')
    # Full old rows, including payloads and timestamps, remain byte-identical.
    digest=__import__('hashlib').sha256()
    ids=[r['document_id'] for r in plan['expected']]
    with c.cursor() as cursor:
        with cursor.copy('COPY (SELECT * FROM earnings_historical_reports WHERE NOT(document_id=ANY(%s::uuid[])) ORDER BY document_id) TO STDOUT (FORMAT binary)',(ids,)) as stream:
            for block in stream:digest.update(block)
    if digest.hexdigest()!=old['earnings'][TABLE]['sha256']:raise ValueError('Historical original rows changed')


def verify(c,plan):
    frozen(plan)
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');live(c,plan)
        if not appended(c,plan):raise ValueError('Backfill incomplete')
        preserved(c,plan)
        if financial.counts(c,[TABLE])[TABLE]!=plan['baseline']['earnings'][TABLE]['rows']+7:raise ValueError('Unexpected history rows')
    return dict(outcome='verified',plan_sha256=base.digest(plan),reports=7,metrics=13)


def apply(c,plan,target_confirmation,hash_confirmation,backup):
    if target_confirmation!=plan['target_label'] or hash_confirmation!=base.digest(plan):raise ValueError('New exact backfill target/hash approval required')
    frozen(plan);backup_check(backup,plan)
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE');c.execute('SET LOCAL search_path=public,pg_catalog')
        c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
        if not c.execute('SELECT pg_try_advisory_xact_lock(726530020)').fetchone()[0]:raise ValueError('Concurrent Earnings writer')
        c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(map(sql.Identifier,sorted(plan['baseline']['earnings'])))))
        live(c,plan)
        if appended(c,plan):preserved(c,plan);return dict(outcome='already_initialized',plan_sha256=hash_confirmation,reports=7,metrics=13)
        if baseline(c)!=plan['baseline']:raise ValueError('Earnings/Forecast baseline changed')
        # Existing E2E approved insertion path; initializer/isolated guard unchanged.
        legacy.import_seed(c,plan['ledger'])
        if not appended(c,plan):raise ValueError('Incomplete history import')
        preserved(c,plan);live(c,plan);frozen(plan)
    return dict(outcome='created',plan_sha256=hash_confirmation,reports=7,metrics=13)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','plan','apply','verify'])
    for name in ('plan','identity','backup','out'):p.add_argument('--'+name,type=Path)
    p.add_argument('--confirm-target');p.add_argument('--confirm-plan');args=p.parse_args()
    if not args.out or args.out.exists():raise ValueError('New output required')
    read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    with get_independent_connection() as c:
        c.read_only=args.command!='apply'
        if args.command=='prepare':result=prepare(c,read(args.identity),read(args.backup))
        elif args.command=='plan':
            plan=read(args.plan);frozen(plan);result=prepare(c,plan['target'],read(args.backup))
            if result!=plan:raise ValueError('Live plan changed')
        elif args.command=='apply':result=apply(c,read(args.plan),args.confirm_target,args.confirm_plan,read(args.backup))
        else:result=verify(c,read(args.plan))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(command=args.command,sha256=base.digest(result) if args.command in ('prepare','plan') else result['plan_sha256'])))
