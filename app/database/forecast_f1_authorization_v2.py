"""Versioned backend-only F1 authorization and explicit legacy migration.

No startup DDL or migration. The immutable legacy policy remains the chain root.
The CLI prepares read-only and requires an exact new plan hash before one INSERT.
"""
import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from psycopg import sql
from psycopg.types.json import Jsonb
from app.database import activate_forecast_f1 as legacy
from app.database import activate_earnings as base, activate_earnings_financials as financial
from app.database.connection import get_independent_connection
from app import forecast_f1 as model

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'config/forecast_f1_runtime_manifest_v2.json'
SOURCE = 'activation-ui-revision'
LOCKS = (726530032, 726530031)
CONDITIONS = dict(version=2, writes='one append-only forecast_refresh_checks authorization revision',
    ddl=False, import_forecasts=False, runtime_token='separate verified enable-runtime',
    locks=list(LOCKS), lock_timeout='5s', statement_timeout='120s',
    post_commit='no automatic restore or rollback', frontend='tested delivery, not worker authorization')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def spec():
    value = read(ROOT / SPEC)
    if set(value) != {'version', 'scope', 'paths', 'versions'} or value['version'] != 2:
        raise ValueError('Unknown F1 backend manifest version')
    paths = value['paths']
    if not isinstance(paths, list) or paths != sorted(set(paths)) or SPEC not in paths:
        raise ValueError('Incomplete F1 backend manifest')
    if any(Path(p).is_absolute() or '..' in Path(p).parts or p.startswith('frontend/') for p in paths):
        raise ValueError('Invalid F1 backend manifest path')
    # The reviewed conservative boundary includes every existing backend module,
    # SQL/config and requirements. New executable/config files fail closed too.
    actual = {str(p.relative_to(ROOT)).replace('\\', '/') for folder in ('app', 'config')
              for p in (ROOT / folder).rglob('*') if p.is_file()
              and p.suffix in ('.py', '.sql', '.json', '.yaml', '.yml') and '__pycache__' not in p.parts}
    if set(paths) != actual | {'requirements.txt'}:
        raise ValueError('Backend dependency inventory changed')
    if value['versions'] != ['httpx', 'psycopg', 'pypdf']:
        raise ValueError('Unknown F1 library manifest')
    return value


def artifacts():
    value = spec()
    import httpx, psycopg, pypdf
    return {**{p:base.file_hash(ROOT / p) for p in value['paths']},
            'httpx_version':httpx.__version__, 'psycopg_version':psycopg.__version__,
            'pypdf_version':pypdf.__version__}


def dependency_audit():
    """Resolve static local imports, including function-local/relative imports.

    Dynamic imports and SQL/config reads stay within the complete reviewed
    app/config inventory, rather than claiming AST analysis alone proves closure.
    """
    paths = set(spec()['paths']); edges = []; dynamic = []
    for path in sorted(p for p in paths if p.endswith('.py')):
        tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
        module = path[:-3].replace('/', '.')
        package = module if path.endswith('/__init__.py') else module.rpartition('.')[0]
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                name = node.module or ''
                if node.level:
                    name = importlib.util.resolve_name('.' * node.level + name, package)
                names = [name] + [name + '.' + alias.name for alias in node.names]
            elif isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                if (getattr(node.func, 'id', '') == '__import__' or getattr(node.func, 'attr', '') in ('import_module', 'read_text', 'read_bytes', 'execute')):
                    dynamic.append([path, node.lineno, ast.dump(node.func)])
            for name in names:
                if name == 'app' or name.startswith('app.'):
                    candidates = [name.replace('.', '/') + '.py', name.replace('.', '/') + '/__init__.py']
                    found = next((p for p in candidates if (ROOT / p).is_file()), None)
                    if found:
                        if found not in paths:raise ValueError('Unprotected transitive import: ' + found)
                        edges.append([path, found])
    return dict(local_import_edges=sorted(edges), dynamic_review_sites=sorted(dynamic),
                frontend_financial_write_path=False,
                boundary='all app/config files plus Python requirements and parser/driver versions; no frontend execution by worker')


def root_policy(c):
    rows = c.execute("SELECT check_id,detail FROM forecast_refresh_checks WHERE source_id='activation-policy'").fetchall()
    if len(rows) != 1:raise ValueError('One original immutable F1 policy required')
    return dict(check_id=str(rows[0][0]), detail=rows[0][1])


def revisions(c):
    rows = c.execute("SELECT check_id,outcome,detail FROM forecast_refresh_checks WHERE source_id=%s", (SOURCE,)).fetchall()
    result = []
    for identifier, outcome, detail in rows:
        if set(detail) != {'plan', 'plan_sha256'} or outcome != 'success' or model.digest(detail['plan']) != detail['plan_sha256']:
            raise ValueError('Partial or invalid F1 authorization revision')
        if str(identifier) != str(uuid5(NAMESPACE_URL, 'f1-authorization-v2:' + detail['plan_sha256'])):
            raise ValueError('Invalid revision identifier')
        result.append(detail)
    result.sort(key=lambda row:row['plan'].get('revision', -1))
    return result


def validate_plan(plan):
    if set(plan) != {'version','ready_for_apply','revision','previous_plan_sha256','target','target_label','original_policy','historical_plan','artifacts','manifest','schema','reference_data','dispatch','protected','conditions','delivery','dependency_audit'}:
        raise ValueError('Incomplete F1 authorization plan')
    if plan['version'] != 2 or plan['ready_for_apply'] is not True or plan['revision'] != 1 or plan['conditions'] != CONDITIONS:
        raise ValueError('Unknown F1 authorization plan')
    if plan['artifacts'] != artifacts() or plan['manifest'] != spec() or plan['dependency_audit'] != dependency_audit():
        raise ValueError('F1 critical backend artifacts changed')
    old = plan['historical_plan']; policy = plan['original_policy']['detail']
    if model.digest(old) != plan['previous_plan_sha256'] or old['artifacts'] != policy['artifacts'] or policy['plan_sha256'] != plan['previous_plan_sha256']:
        raise ValueError('Historical F1 plan/policy mismatch')
    if policy['target'] != old['target'] or plan['target_label'] != base.target_label(plan['target']):
        raise ValueError('F1 historical target mismatch')
    if plan['target'] != old['target']:
        target=plan['target']
        if not (target['database'].startswith('macrolens_forecast_f1_ui_') and target['user']=='macrolens_ci'
                and target['host'] in ('localhost','127.0.0.1') and target['port']!=5432):
            raise ValueError('Only an explicitly owned clone may retain a different historical source identity')
    if old['dispatch'] != plan['dispatch'] or policy['dispatch'] != plan['dispatch'] or plan['dispatch'] != legacy.policy():
        raise ValueError('F1 source policy changed')
    if policy['reference_data'] != plan['reference_data'] or old['reference_data'] != plan['reference_data']:
        raise ValueError('F1 historical references changed')
    if model.digest(plan['schema']) != policy['schema_sha256'] or old['reference']['after'] != plan['schema']:
        raise ValueError('F1 historical schema mismatch')
    if old['ledger']['records'] != legacy.seed():raise ValueError('F1 seed ledger changed')


def check_live(c, plan):
    validate_plan(plan)
    if not 170000 <= c.info.server_version < 180000 or base.target_identity(c) != plan['target']:
        raise ValueError('Exact F1 PostgreSQL identity required')
    if root_policy(c) != plan['original_policy'] or legacy.schema_state(c) != plan['schema'] or legacy.reference_data(c) != plan['reference_data']:
        raise ValueError('F1 policy/schema/reference data changed')


def token_for(plan):
    return dict(version=2, plan_sha256=model.digest(plan), target=plan['target'], artifacts=plan['artifacts'])


def authorized(c, token, check_schema=True):
    if set(token) != {'version','plan_sha256','target','artifacts'} or token['version'] != 2 or token['artifacts'] != artifacts():
        raise ValueError('F1 runtime backend manifest/token changed')
    rows = revisions(c)
    # This first migration has one explicit predecessor. Future security changes
    # need another reviewed protocol, not an unrestricted auto-approval chain.
    if len(rows) != 1:raise ValueError('One complete linked F1 revision required')
    plan = rows[0]['plan']
    if token != token_for(plan):raise ValueError('Stale or foreign F1 runtime token')
    check_live(c, plan)  # schema check is mandatory for V2, including direct writers
    return plan


def check_backup(backup, plan):
    financial.check_backup(backup, plan['target'])
    if any(backup['source_snapshots'].get(t) != snapshot for t,snapshot in plan['protected'].items()):
        raise ValueError('Backup F1 data differ from migration plan')


def prepare(c, historical, delivery, backup):
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if revisions(c):raise ValueError('Revision present: use verify')
        plan = dict(version=2, ready_for_apply=True, revision=1,
            previous_plan_sha256=model.digest(historical), target=base.target_identity(c),
            target_label=base.target_label(base.target_identity(c)), original_policy=root_policy(c),
            historical_plan=historical, artifacts=artifacts(), manifest=spec(),
            schema=legacy.schema_state(c), reference_data=legacy.reference_data(c),
            dispatch=legacy.policy(), protected=financial.table_snapshots(c, model.TABLES),
            conditions=CONDITIONS, delivery=delivery, dependency_audit=dependency_audit())
        check_live(c, plan);check_backup(backup, plan)
    return plan


def verify(c, plan):
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        authorized(c, token_for(plan))
        rows = revisions(c)
        if rows != [dict(plan=plan, plan_sha256=model.digest(plan))]:raise ValueError('Foreign/conflicting revision')
        snapshots = financial.table_snapshots(c, ('forecast_vintages','forecast_freezes'))
        if any(snapshots[t] != plan['protected'][t] for t in snapshots):raise ValueError('Forecast data changed during cutover')
    return dict(outcome='verified', plan_sha256=model.digest(plan), runtime_token=token_for(plan))


def apply(c, plan, target_confirmation, hash_confirmation, backup):
    if target_confirmation != plan['target_label'] or hash_confirmation != model.digest(plan):
        raise ValueError('Separate exact F1 revision target/hash approval required')
    validate_plan(plan);check_backup(backup, plan)
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE')
        c.execute("SET LOCAL search_path TO public,pg_catalog")
        c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
        for lock in LOCKS:
            if not c.execute('SELECT pg_try_advisory_xact_lock(%s)', (lock,)).fetchone()[0]:raise ValueError('Concurrent F1 revision/worker')
        c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in (*legacy.REF_TABLES,*legacy.MACRO_REF_TABLES,'forecast_vintages','forecast_freezes'))))
        c.execute('LOCK TABLE forecast_refresh_checks IN SHARE ROW EXCLUSIVE MODE')
        check_live(c, plan)
        existing = revisions(c)
        if existing:
            if existing != [dict(plan=plan,plan_sha256=hash_confirmation)]:raise ValueError('Conflicting F1 revision')
            return dict(outcome='already_initialized',plan_sha256=hash_confirmation,runtime_token=token_for(plan))
        if financial.table_snapshots(c,model.TABLES) != plan['protected']:raise ValueError('F1 data changed since prepare')
        c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,%s,'success','2099-01-01',%s)",
            (uuid5(NAMESPACE_URL,'f1-authorization-v2:'+hash_confirmation),SOURCE,Jsonb(dict(plan=plan,plan_sha256=hash_confirmation))))
        check_live(c, plan)
        if revisions(c) != [dict(plan=plan,plan_sha256=hash_confirmation)]:raise ValueError('Revision postcondition failed')
    return dict(outcome='created',plan_sha256=hash_confirmation,runtime_token=token_for(plan))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','plan','apply','verify','enable-runtime'])
    for arg in ('plan','historical','delivery','backup','out'):parser.add_argument('--'+arg,type=Path)
    parser.add_argument('--confirm-target');parser.add_argument('--confirm-plan')
    args=parser.parse_args()
    if not args.out or args.out.exists():raise ValueError('New explicit output required')
    with get_independent_connection() as c:
        c.read_only=args.command!='apply'
        if args.command=='prepare':result=prepare(c,read(args.historical),read(args.delivery),read(args.backup))
        else:
            plan=read(args.plan)
            if args.command=='plan':
                result=prepare(c,plan['historical_plan'],plan['delivery'],read(args.backup))
                if result!=plan:raise ValueError('Live plan changed')
            elif args.command=='apply':result=apply(c,plan,args.confirm_target,args.confirm_plan,read(args.backup))
            else:
                result=verify(c,plan)
                if args.command=='enable-runtime':
                    if args.confirm_target!=plan['target_label'] or args.confirm_plan!=model.digest(plan):raise ValueError('Explicit runtime approval required')
                    from app.forecast_f1_runtime import TOKEN
                    if args.out.resolve()!=TOKEN.resolve():raise ValueError('Exact runtime token path required')
                    result=result['runtime_token']
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(command=args.command,sha256=model.digest(result) if args.command in ('prepare','plan') else result.get('plan_sha256'))))


if __name__=='__main__':main()
