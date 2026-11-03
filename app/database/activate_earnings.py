"""Explicit, planned E2A activation. Preparing a plan is read-only.

The isolated-only initializer is intentionally not used or relaxed here.
Apply requires the exact target, approved plan hash, unchanged artifacts and
a verified local backup manifest. This module never contacts an IR/SEC source.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg.pq import TransactionStatus
from app import earnings
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).with_name('earnings_schema.sql')
TABLES = ('earnings_companies', 'earnings_company_aliases', 'earnings_periods',
          'earnings_events', 'earnings_source_evidence', 'earnings_date_confirmations')
ARTIFACTS = ('app/database/activate_earnings.py', 'app/database/earnings_schema.sql',
             'app/database/earnings_activation_rollback.sql',
             'app/earnings.py', 'config/earnings_manual.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str,
                                    separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def artifacts():
    return {name: file_hash(ROOT / name) for name in ARTIFACTS}


def target_identity(connection):
    row = connection.execute('''SELECT current_database(),current_user,
        (SELECT oid FROM pg_database WHERE datname=current_database()),
        system_identifier::text FROM pg_control_system()''').fetchone()
    params = connection.info.get_parameters()
    return dict(host=params.get('host', 'localhost'), port=int(params.get('port', 5432)),
                database=row[0], user=row[1], database_oid=row[2], system_identifier=row[3])


def target_label(target):
    return f"{target['host']}:{target['port']}/{target['database']}"


def catalog(connection, earnings_only):
    """OID-independent schema signature, including bodies, FKs, indexes and triggers."""
    condition = "left(c.relname,9)='earnings_'" if earnings_only else "left(c.relname,9)<>'earnings_'"
    relation_filter = "n.nspname='public' AND " + condition
    relations = connection.execute('''SELECT c.relname,c.relkind FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + relation_filter + ' ORDER BY 1,2').fetchall()
    columns = connection.execute('''SELECT c.relname,a.attnum,a.attname,
        format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid)
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE a.attnum>0 AND NOT a.attisdropped AND c.relkind IN ('r','p') AND '''
        + relation_filter + ' ORDER BY 1,2').fetchall()
    constraints = connection.execute('''SELECT c.relname,k.conname,pg_get_constraintdef(k.oid)
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + relation_filter + ' ORDER BY 1,2').fetchall()
    indexes = connection.execute('''SELECT c.relname,pg_get_indexdef(i.indexrelid)
        FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + relation_filter + ' ORDER BY 1,2').fetchall()
    triggers = connection.execute('''SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND '''
        + relation_filter + ' ORDER BY 1,2').fetchall()
    function_condition = "left(p.proname,9)='earnings_'" if earnings_only else "left(p.proname,9)<>'earnings_'"
    functions = connection.execute('''SELECT p.proname,pg_get_function_identity_arguments(p.oid),
        p.prosrc,p.provolatile,p.prosecdef,p.proconfig FROM pg_proc p
        JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND '''
        + function_condition + ' ORDER BY 1,2').fetchall()
    return dict(relations=relations, columns=columns, constraints=constraints,
                indexes=indexes, triggers=triggers, functions=functions)


def inspect(connection):
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError('Preflight requires a fresh connection with no active transaction')
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        target = target_identity(connection)
        reserved = connection.execute('''SELECT n.nspname,c.relname,c.relkind::text
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE left(c.relname,9)='earnings_' AND n.nspname NOT IN ('pg_catalog','information_schema')
            UNION ALL SELECT n.nspname,p.proname,'function' FROM pg_proc p
            JOIN pg_namespace n ON n.oid=p.pronamespace WHERE left(p.proname,9)='earnings_'
            AND n.nspname NOT IN ('pg_catalog','information_schema') ORDER BY 1,2''').fetchall()
        tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND left(tablename,9)='earnings_' ORDER BY tablename").fetchall()
        return dict(target=target, existing_objects=reserved, existing_tables=[r[0] for r in tables],
                    earnings_schema_signature=digest(catalog(connection, True)),
                    macro_schema_signature=digest(catalog(connection, False)),
                    read_only=connection.execute('SHOW transaction_read_only').fetchone()[0])


def check_backup(manifest, target):
    if manifest['target'] != target or manifest.get('format') != 'pg_dump_custom' or manifest.get('toc_verified') is not True:
        raise ValueError('Backup must identify this exact cluster/database and have a verified restore TOC')
    path = Path(manifest['path'])
    with path.open('rb') as stream:
        if stream.read(5) != b'PGDMP':
            raise ValueError('Backup is not a custom pg_dump archive')
    if path.stat().st_size != manifest['bytes'] or file_hash(path) != manifest['sha256']:
        raise ValueError('Backup size/hash mismatch')


def prepare(connection, backup, expected_signature):
    state = inspect(connection)
    check_backup(backup, state['target'])
    if len(expected_signature) != 64 or any(c not in '0123456789abcdef' for c in expected_signature):
        raise ValueError('A schema signature from isolated validation is required')
    if state['existing_objects'] and (set(state['existing_tables']) != set(TABLES) or state['earnings_schema_signature'] != expected_signature):
        raise ValueError('Partial, conflicting or unexpected Earnings schema; refuse activation')
    rows = json.loads(earnings.DATA.read_text(encoding='utf-8'))
    for row in rows:
        earnings.validate(row)
    return dict(version=1, created_at=datetime.now(timezone.utc).isoformat(),
                target=state['target'], target_label=target_label(state['target']),
                preflight=state, backup=backup, artifacts=artifacts(),
                expected_earnings_schema_signature=expected_signature,
                ddl_tables=list(TABLES), seed_events=len(rows), seed_companies=len({r['cik'] for r in rows}))


def apply(connection, plan, confirmed_target, confirmed_plan):
    """The sole write path: never called by prepare, API, startup or tests on user DB."""
    if confirmed_target != plan['target_label'] or confirmed_plan != digest(plan):
        raise ValueError('Explicit target and exact approved plan hash are required')
    if plan['version'] != 1 or plan['artifacts'] != artifacts():
        raise ValueError('Activation artifacts changed after review; prepare a new plan')
    check_backup(plan['backup'], plan['target'])
    state = inspect(connection)
    if state['target'] != plan['target']:
        raise ValueError('Database/cluster/role changed after preflight')
    if state['macro_schema_signature'] != plan['preflight']['macro_schema_signature']:
        raise ValueError('Existing macro schema changed after review; prepare a new plan')
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ WRITE')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute("SET LOCAL lock_timeout TO '5s'")
        connection.execute("SET LOCAL statement_timeout TO '120s'")
        # Existing shared lease prevents a normal refresh job starting during activation.
        connection.execute('SELECT pg_advisory_xact_lock(726530019)')
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        if target_identity(connection) != plan['target']:
            raise ValueError('Target identity changed')
        before_macro = digest(catalog(connection, False))
        existing = catalog(connection, True)
        if not existing['relations'] and not existing['functions']:
            connection.execute(SCHEMA.read_text(encoding='utf-8'))
            outcome = 'created'
        elif digest(existing) == plan['expected_earnings_schema_signature']:
            outcome = 'already_initialized'
        else:
            raise ValueError('Unexpected Earnings objects appeared; no DDL applied')
        if digest(catalog(connection, True)) != plan['expected_earnings_schema_signature']:
            raise ValueError('Created schema differs from the isolated validated schema')
        earnings.import_records(connection, json.loads(earnings.DATA.read_text(encoding='utf-8')))
        if digest(catalog(connection, False)) != before_macro:
            raise ValueError('Existing schema changed; rolling back activation')
        counts = {name: connection.execute('SELECT count(*) FROM public.' + name).fetchone()[0] for name in TABLES}
    return dict(outcome=outcome, target=plan['target'], counts=counts, approved_plan=digest(plan))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    dry = commands.add_parser('prepare', help='Read-only preflight and plan; never runs DDL')
    dry.add_argument('--backup-manifest', type=Path, required=True)
    dry.add_argument('--schema-reference', type=Path, required=True)
    dry.add_argument('--out', type=Path, required=True)
    write = commands.add_parser('apply', help='Requires prior explicit approval of this target and plan')
    write.add_argument('--plan', type=Path, required=True)
    write.add_argument('--confirm-target', required=True)
    write.add_argument('--confirm-plan', required=True)
    args = parser.parse_args()
    with get_independent_connection() as connection:
        if args.command == 'prepare':
            backup = json.loads(args.backup_manifest.read_text(encoding='utf-8'))
            reference = json.loads(args.schema_reference.read_text(encoding='utf-8'))
            plan = prepare(connection, backup, reference['earnings_schema_signature'])
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(plan, stream, indent=2, default=str)
            print(json.dumps(dict(target=plan['target_label'], plan_sha256=digest(plan),
                                  tables=plan['ddl_tables'], mode='read_only_plan')))
        else:
            plan = json.loads(args.plan.read_text(encoding='utf-8'))
            print(json.dumps(apply(connection, plan, args.confirm_target, args.confirm_plan)))


if __name__ == '__main__':
    main()
