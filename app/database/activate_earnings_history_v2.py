"""Scoped E2E V2. Prepare is read-only; normal apply needs a NEW explicit hash.

V1 is retained unchanged. Backup evidence is checked separately from the
canonical plan so unrelated macro rows/timestamps never enter its hash.
"""
import argparse
import json
from pathlib import Path
from psycopg import sql
from app.database import activate_earnings_history as legacy
from app.database import activate_earnings as base, activate_earnings_financials as financial
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = tuple(sorted(legacy.BEFORE))
TABLE = 'earnings_historical_reports'
ARTIFACTS = (*legacy.ARTIFACTS, 'app/database/activate_earnings_history_v2.py')
CONDITIONS = dict(isolation='READ COMMITTED', advisory_lock=726530020,
                  table_lock='SHARE', lock_timeout='5s', statement_timeout='120s',
                  write_tables=[TABLE], preserve_tables=list(PROTECTED),
                  backup='separate verified full PG17 restore; exact protected baseline',
                  abort_on=['target', 'artifacts', 'ledger', 'DDL', 'Earnings data',
                            'schema/dependencies', 'partial store', 'concurrent import', 'lock timeout'],
                  recheck='after all Earnings locks, before DDL and before COMMIT',
                  post_commit='verify exact seed and protected state; never automatic restore')


def artifacts():
    return {p: base.file_hash(ROOT / p) for p in ARTIFACTS}


def dependencies(connection):
    """Actual pg_depend closure, not a table-name exclusion heuristic."""
    rows = connection.execute('''WITH RECURSIVE roots(classid,objid,objsubid) AS (
      SELECT 'pg_class'::regclass::oid,c.oid,0 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
       WHERE n.nspname='public' AND left(c.relname,9)='earnings_'
      UNION SELECT 'pg_constraint'::regclass::oid,k.oid,0 FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
       JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND left(c.relname,9)='earnings_'
      UNION SELECT 'pg_trigger'::regclass::oid,t.oid,0 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
       JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND left(c.relname,9)='earnings_' AND NOT t.tgisinternal
      UNION SELECT 'pg_proc'::regclass::oid,p.oid,0 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
       WHERE n.nspname='public' AND left(p.proname,9)='earnings_'
    ), closure(classid,objid,objsubid) AS (
      SELECT * FROM roots UNION SELECT d.refclassid,d.refobjid,d.refobjsubid
       FROM pg_depend d JOIN closure q ON d.classid=q.classid AND d.objid=q.objid
    ) SELECT DISTINCT pg_describe_object(d.classid,d.objid,d.objsubid),
       pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid),d.deptype
       FROM pg_depend d JOIN closure q ON d.classid=q.classid AND d.objid=q.objid ORDER BY 1,2,3''').fetchall()
    fks = connection.execute('''SELECT c.relname,k.conname,tn.nspname,t.relname,pg_get_constraintdef(k.oid)
       FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
       JOIN pg_class t ON t.oid=k.confrelid JOIN pg_namespace tn ON tn.oid=t.relnamespace
       WHERE n.nspname='public' AND left(c.relname,9)='earnings_' AND k.contype='f' ORDER BY 1,2''').fetchall()
    if any(schema != 'public' or target not in (*PROTECTED, TABLE) for _, _, schema, target, _ in fks):
        raise ValueError('Unreviewed external Earnings FK dependency')
    triggers = connection.execute('''SELECT c.relname,
       CASE WHEN t.tgisinternal THEN k.conname||':'||t.tgfoid::regproc::text ELSE t.tgname END,
       t.tgenabled,t.tgisinternal
       FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
       LEFT JOIN pg_constraint k ON k.oid=t.tgconstraint
       WHERE n.nspname='public' AND left(c.relname,9)='earnings_' ORDER BY 1,2''').fetchall()
    indexes = connection.execute('''SELECT c.relname,i.indisvalid,i.indisready,i.indislive
       FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_class t ON t.oid=i.indrelid
       JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' AND left(t.relname,9)='earnings_' ORDER BY 1''').fetchall()
    return json.loads(json.dumps(dict(edges=rows, foreign_keys=fks, trigger_state=triggers, index_state=indexes)))


def schema_state(connection):
    foreign = connection.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE left(c.relname,9)='earnings_' AND n.nspname NOT IN ('public','pg_catalog','information_schema')").fetchone()[0]
    if foreign:
        raise ValueError('Foreign Earnings objects')
    return dict(catalog=base.catalog(connection, True), dependencies=dependencies(connection))


def reference(connection):
    before = schema_state(connection)
    connection.rollback()
    with connection.transaction(force_rollback=True):
        legacy.reports.initialize_isolated(connection)
        legacy.import_seed(connection, legacy.seed())
        after = schema_state(connection)
    result = json.loads(json.dumps(dict(before=before, after=after)))
    legacy.check_reference({k:dict(catalog=v['catalog']) for k,v in result.items()})
    return result


def phase(connection, ref):
    state = schema_state(connection)
    for key in ('before', 'after'):
        if base.digest(state) == base.digest(ref[key]):
            return key
    raise ValueError('Protected schema/dependencies changed or partial store')


def prepare(connection, expected_target, ref):
    # A single consistent READ ONLY view; no macro data or volatile timestamp.
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        if base.target_identity(connection) != expected_target or not 170000 <= connection.info.server_version < 180000:
            raise ValueError('Exact target / PostgreSQL 17 required')
        if phase(connection, ref) != 'before':
            raise ValueError('Expected uninitialized E2E store')
        snapshots = financial.table_snapshots(connection, PROTECTED)
        if set(snapshots) != set(PROTECTED) or financial.counts(connection, PROTECTED) != legacy.BEFORE:
            raise ValueError('Unexpected protected Earnings baseline')
        records = legacy.seed()
        for r in records:
            actual = connection.execute('SELECT cik,ticker FROM public.earnings_companies WHERE company_id=%s', (legacy.reports.identity(r['cik']),)).fetchone()
            if actual != (r['cik'], r['ticker']):
                raise ValueError('Issuer FK identity mismatch')
    return dict(version=2, ready_for_apply=True, status='awaiting_new_explicit_approval',
                target=expected_target, target_label=base.target_label(expected_target),
                artifacts=artifacts(), protected_snapshots=snapshots, reference=ref,
                ddl=dict(text=legacy.reports.SCHEMA.read_text(encoding='utf-8'), sha256=base.file_hash(legacy.reports.SCHEMA)),
                ledger=dict(records=records, sha256=base.file_hash(legacy.reports.DATA), fingerprint=base.digest(records)),
                seed_manifest=legacy.manifest(records), expected_counts=legacy.AFTER, conditions=CONDITIONS)


def check_backup(backup, plan):
    proof = financial.check_backup(backup, plan['target'])
    protected = {k:v for k,v in proof['source_snapshots'].items() if k in PROTECTED}
    if protected != plan['protected_snapshots'] or proof['source_earnings_signature'] != base.digest(plan['reference']['before']['catalog']):
        raise ValueError('Backup protected state differs from plan')
    return proof


def apply(connection, plan, confirmed_target, confirmed_plan, backup):
    if confirmed_target != plan['target_label'] or confirmed_plan != base.digest(plan):
        raise ValueError('NEW explicit V2 target and full hash required')
    if plan.get('version') != 2 or plan.get('ready_for_apply') is not True or plan['artifacts'] != artifacts() or plan['conditions'] != CONDITIONS:
        raise ValueError('Frozen V2 artifacts/conditions changed')
    records = legacy.seed()
    if (plan['ledger'] != dict(records=records, sha256=base.file_hash(legacy.reports.DATA), fingerprint=base.digest(records))
        or plan['seed_manifest'] != legacy.manifest(records) or plan['expected_counts'] != legacy.AFTER
        or plan['ddl'] != dict(text=legacy.reports.SCHEMA.read_text(encoding='utf-8'), sha256=base.file_hash(legacy.reports.SCHEMA))):
        raise ValueError('Exact V2 DDL/ledger/metric manifest changed')
    check_backup(backup, plan)
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute("SET LOCAL lock_timeout TO '5s'")
        connection.execute("SET LOCAL statement_timeout TO '120s'")
        if not connection.execute('SELECT pg_try_advisory_xact_lock(726530020)').fetchone()[0]:
            raise ValueError('Concurrent Earnings activation/import')
        # Lock BEFORE reading protected data: READ COMMITTED then sees any
        # writer which committed while acquisition was waiting. SHARE blocks
        # Earnings DML/DDL, permits normal GET, and touches no macro table.
        connection.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier('public', t) for t in PROTECTED)))
        if base.target_identity(connection) != plan['target'] or not 170000 <= connection.info.server_version < 180000:
            raise ValueError('Target changed')
        current = phase(connection, plan['reference'])
        if financial.table_snapshots(connection, PROTECTED) != plan['protected_snapshots']:
            raise ValueError('Protected Earnings data changed')
        if current == 'before':
            connection.execute(plan['ddl']['text'])
        else:
            connection.execute(sql.SQL('LOCK TABLE public.{} IN SHARE MODE').format(sql.Identifier(TABLE)))
            legacy.verify_seed(connection, plan['seed_manifest'])
        before = financial.table_snapshots(connection, [TABLE]) if current == 'after' else None
        legacy.import_seed(connection, records)
        legacy.verify_seed(connection, plan['seed_manifest'])
        after = financial.table_snapshots(connection, [TABLE])
        if (financial.table_snapshots(connection, PROTECTED) != plan['protected_snapshots']
            or phase(connection, plan['reference']) != 'after'
            or financial.counts(connection, legacy.AFTER) != legacy.AFTER
            or current == 'after' and before != after):
            raise ValueError('Post-import protected state differs; rollback')
        result = dict(outcome='created' if current == 'before' else 'already_initialized',
                      plan_sha256=confirmed_plan, target=plan['target'], counts=legacy.AFTER,
                      history_snapshot=after, protected_snapshots=plan['protected_snapshots'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'apply'])
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--identity', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--confirm-target')
    parser.add_argument('--confirm-plan')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Refuse overwrite')
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    with get_independent_connection() as c:
        if args.command == 'prepare':
            c.read_only = True
            result = prepare(c, read(args.identity), read(args.reference))
            check_backup(read(args.backup), result)
        else:
            result = apply(c, read(args.plan), args.confirm_target, args.confirm_plan, read(args.backup))
    with args.out.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
    print(json.dumps({'mode': args.command, 'plan_sha256': base.digest(result) if args.command == 'prepare' else args.confirm_plan}))


if __name__ == '__main__':
    main()
