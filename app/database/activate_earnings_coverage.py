"""Explicit E2C activation. Prepare is read-only; apply needs an approved plan.

Never called by API/startup. Isolated importer/initializer guards stay intact.
Successful COMMIT is never automatically reversed. No publisher HTTP.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg import sql
from app import earnings_coverage as coverage
from app.database import activate_earnings as base
from app.database import activate_earnings_financials as financial
from app.database.connection import get_independent_connection

ROOT = Path(__file__).resolve().parents[2]
TABLES = tuple(financial.EXPECTED_AFTER)
BEFORE = financial.EXPECTED_AFTER
AFTER = dict(zip(TABLES, (53,55,37,37,40,66,6,12)))
CONSTRAINT = 'earnings_date_confirmations_source_timezone_check'
ARTIFACTS = (
    'app/database/activate_earnings_coverage.py',
    'app/database/activate_earnings.py', 'app/database/activate_earnings_financials.py',
    'app/database/earnings_schema.sql', 'app/database/earnings_financial_schema.sql',
    'app/database/earnings_coverage_schema.sql', 'app/earnings_coverage.py',
    'app/earnings.py', 'app/earnings_financials.py',
    'config/earnings_manual.json', 'config/earnings_financial_manual.json',
    'config/earnings_companies_reviewed.json', 'config/earnings_dates_reviewed.json',
    'docs/audits/equity-earnings-coverage-activation-rollback-2026-11-04.md')


def artifacts():
    return {p: base.file_hash(ROOT / p) for p in ARTIFACTS}


def definition(zones):
    return "CHECK ((source_timezone = ANY (ARRAY[" + ', '.join("'" + z + "'::text" for z in zones) + "])))"


def timezone_check(connection):
    row = connection.execute("SELECT pg_get_constraintdef(oid),convalidated FROM pg_constraint WHERE conrelid='public.earnings_date_confirmations'::regclass AND conname=%s", (CONSTRAINT,)).fetchone()
    if not row or not row[1]:
        raise ValueError('Missing or unvalidated timezone CHECK')
    return row[0]


def seed():
    companies = coverage.registry()
    rows = json.loads(coverage.DATA.read_text(encoding='utf-8'))
    checked = [coverage.validate(r, companies) for r in rows]
    keys = {(r['cik'], r['fiscal_year'], r['fiscal_quarter']) for r in checked}
    if len(companies) != 53 or sum(len(c['aliases']) for c in companies.values()) != 55 or len(checked) != 27 or len(keys) != 27 or len({r['cik'] for r in checked}) != 27:
        raise ValueError('Seed differs from the reviewed 53 issuers / 27 dated periods')
    for aliases in ({'GOOG','GOOGL'}, {'BRK.B','BRK-B'}):
        if sum(aliases <= set(c['aliases']) for c in companies.values()) != 1:
            raise ValueError('Share class aliases must identify one issuer')
    return rows


def rows(connection):
    return {t: [r[0] for r in connection.execute(sql.SQL('SELECT row_to_json(t)::text FROM public.{} t ORDER BY row_to_json(t)::text').format(sql.Identifier(t)))] for t in TABLES}


def expected_rows(plan, phase):
    return {t: sorted(plan['original_rows'][t] + (plan['additions'][t] if phase == 'e2c' else [])) for t in TABLES}


def check_reference(reference):
    # A complete executed reference is required, with only the reviewed CHECK change.
    old, new = reference['e2b_catalog'], reference['e2c_catalog']
    if set(old) != set(new):
        raise ValueError('Reference catalogs differ')
    expected = json.loads(json.dumps(old))
    found = 0
    for item in expected['constraints']:
        if item[0] == 'earnings_date_confirmations' and item[1] == CONSTRAINT:
            if item[2] != definition(coverage.ZONE_ORDER[:2]):
                raise ValueError('Reference old CHECK differs')
            item[2] = definition(coverage.ZONE_ORDER)
            found += 1
    if found != 1 or base.digest(expected) != base.digest(new):
        raise ValueError('Only the reviewed timezone CHECK may change')
    additions = reference['additions']
    if set(additions) != set(TABLES) or {t: len(additions[t]) for t in TABLES} != {t: AFTER[t] - BEFORE[t] for t in TABLES}:
        raise ValueError('Unexpected reference additions')


def prepare(connection, expected_target, backup, reference):
    state = base.inspect(connection)
    if state['target'] != expected_target:
        raise ValueError('Explicit identity differs from live database/cluster/OID/role')
    check_reference(reference)
    proof = financial.check_backup(backup, expected_target)
    if proof['source_earnings_signature'] != state['earnings_schema_signature'] or proof['source_macro_signature'] != state['macro_schema_signature']:
        raise ValueError('Backup schema differs from live schema')
    seed()
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        if base.target_identity(connection) != expected_target or base.digest(base.catalog(connection, True)) != base.digest(reference['e2b_catalog']) or base.digest(base.catalog(connection, False)) != state['macro_schema_signature']:
            raise ValueError('Unexpected/partial schema or changed identity')
        if timezone_check(connection) != definition(coverage.ZONE_ORDER[:2]):
            raise ValueError('E2C is already/partially activated or CHECK is foreign')
        snapshots = financial.table_snapshots(connection)
        if snapshots != backup['source_snapshots'] or financial.counts(connection, TABLES) != BEFORE or len(set(snapshots) - set(TABLES)) != 13:
            raise ValueError('Data changed since backup or unexpected table counts')
        original = rows(connection)
        for cik, company in coverage.registry().items():
            company_id = coverage.dates.identity(cik)
            stored = connection.execute('SELECT company_id,ticker FROM earnings_companies WHERE cik=%s',(cik,)).fetchone()
            if stored and (str(stored[0]),stored[1]) != (company_id,company['ticker']):
                raise ValueError('Existing issuer identity conflicts with reviewed registry')
            for alias in company['aliases']:
                if (connection.execute('SELECT 1 FROM earnings_company_aliases WHERE ticker=%s AND company_id<>%s',(alias,company_id)).fetchone()
                    or connection.execute('SELECT 1 FROM earnings_companies WHERE ticker=%s AND company_id<>%s',(alias,company_id)).fetchone()):
                    raise ValueError('Alias already belongs to a different issuer')
        # No pre-existing row may be silently swallowed by INSERT ON CONFLICT.
        for t in TABLES:
            pk = next(c[2] for c in reference['e2b_catalog']['columns'] if c[0] == t and c[1] == 1)
            known = {json.loads(r)[pk] for r in original[t]}
            if any(json.loads(r)[pk] in known for r in reference['additions'][t]):
                raise ValueError('New identifier conflicts with existing data')
        financial.verify_seed(connection, financial.seed())
    return dict(version=1, prepared_at=datetime.now(timezone.utc).isoformat(),
                ready_for_apply=True, status='awaiting_explicit_approval_not_executed',
                target=expected_target, target_label=base.target_label(expected_target),
                artifacts=artifacts(), backup=backup, reference=reference,
                source_snapshots=snapshots, original_rows=original,
                additions=reference['additions'], expected_counts=AFTER,
                macro_signature=state['macro_schema_signature'],
                existing_objects=state['existing_objects'],
                ddl=dict(table='earnings_date_confirmations', constraint=CONSTRAINT,
                         before=definition(coverage.ZONE_ORDER[:2]), after=definition(coverage.ZONE_ORDER)))


def apply(connection, plan, confirmed_target, confirmed_plan):
    if confirmed_target != plan['target_label'] or confirmed_plan != base.digest(plan):
        raise ValueError('Explicit target and full approved plan hash required')
    if plan['version'] != 1 or plan.get('ready_for_apply') is not True or plan['artifacts'] != artifacts():
        raise ValueError('Frozen artifacts or plan readiness changed')
    financial.check_backup(plan['backup'], plan['target'])
    check_reference(plan['reference'])
    data = seed()
    state = base.inspect(connection)
    if state['target'] != plan['target'] or state['macro_schema_signature'] != plan['macro_signature'] or base.digest(state['existing_objects']) != base.digest(plan['existing_objects']):
        raise ValueError('Target/schema/objects differ from approved plan')
    signatures = {p: base.digest(plan['reference'][p + '_catalog']) for p in ('e2b','e2c')}
    phase = next((p for p in signatures if signatures[p] == state['earnings_schema_signature']), None)
    if not phase:
        raise ValueError('Partial or foreign Earnings schema')
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ WRITE')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute("SET LOCAL lock_timeout TO '5s'")
        connection.execute("SET LOCAL statement_timeout TO '120s'")
        connection.execute('SELECT pg_advisory_xact_lock(726530019)')
        connection.execute('SELECT pg_advisory_xact_lock(726530020)')
        if base.target_identity(connection) != plan['target'] or base.digest(base.catalog(connection, True)) != signatures[phase] or base.digest(base.catalog(connection, False)) != plan['macro_signature']:
            raise ValueError('Identity/schema changed before write transaction')
        macro = set(plan['source_snapshots']) - set(TABLES)
        before = financial.table_snapshots(connection)
        expected_macro = {t: plan['source_snapshots'][t] for t in macro}
        if set(before) != set(plan['source_snapshots']) or financial.table_snapshots(connection, macro) != expected_macro or rows(connection) != expected_rows(plan, phase):
            raise ValueError('Data changed since approval; no automatic repair')
        if phase == 'e2b':
            if before != plan['source_snapshots'] or timezone_check(connection) != plan['ddl']['before']:
                raise ValueError('Baseline snapshot/CHECK changed')
            connection.execute(coverage.SCHEMA.read_text(encoding='utf-8'))
        coverage.import_records(connection, data)
        if (financial.counts(connection, TABLES) != AFTER
            or rows(connection) != expected_rows(plan, 'e2c')
            or base.digest(base.catalog(connection, True)) != signatures['e2c']
            or base.digest(base.catalog(connection, False)) != plan['macro_signature']
            or financial.table_snapshots(connection, macro) != expected_macro
            or timezone_check(connection) != plan['ddl']['after']):
            raise ValueError('Result differs from reviewed seed or original data; rollback')
        after = financial.table_snapshots(connection)
        if phase == 'e2c' and after != before:
            raise ValueError('Idempotent repeat changed data')
        receipt = dict(outcome='created' if phase == 'e2b' else 'already_initialized',
                       target=plan['target'], approved_plan=confirmed_plan, counts=AFTER,
                       after_snapshots=after, additions=plan['additions'])
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    dry = commands.add_parser('prepare')
    for name in ('identity','backup-manifest','schema-reference','out'):
        dry.add_argument('--' + name, type=Path, required=True)
    write = commands.add_parser('apply')
    write.add_argument('--plan', type=Path, required=True)
    write.add_argument('--confirm-target', required=True)
    write.add_argument('--confirm-plan', required=True)
    write.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    destination = args.out if args.command == 'prepare' else args.receipt
    if destination.exists():
        raise ValueError('Output already exists; refuse to overwrite')
    with get_independent_connection() as connection:
        if args.command == 'prepare':
            connection.read_only = True
            result = prepare(connection, read(args.identity), read(args.backup_manifest), read(args.schema_reference))
        else:
            result = apply(connection, read(args.plan), args.confirm_target, args.confirm_plan)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, default=str)
    print(json.dumps({'mode':args.command, 'plan_sha256':base.digest(result) if args.command == 'prepare' else args.confirm_plan}))


if __name__ == '__main__':
    main()
