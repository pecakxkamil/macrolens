"""Read-only E2B activation proposal. Deliberately provides no apply command."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from app.database import activate_earnings as activation
from app.database.connection import get_independent_connection
from app import earnings_financials as financials

FILES=('app/database/earnings_financial_schema.sql','app/earnings_financials.py',
       'app/earnings.py','config/earnings_financial_manual.json',
       'app/database/prepare_earnings_financials.py')


def prepare(connection, confirmed_target):
    """Inspect a fresh connection. Existing E2B/partial schemas require separate review."""
    state=activation.inspect(connection)
    if activation.target_label(state['target'])!=confirmed_target:
        raise ValueError('Target differs from the explicitly named database')
    if set(state['existing_tables'])!=set(activation.TABLES):
        raise ValueError('Requires the complete E2A schema and no financial schema')
    if any(name.startswith('earnings_financial_') for _,name,_ in state['existing_objects']):
        raise ValueError('Financial object name collision')
    records=json.loads(financials.DATA.read_text(encoding='utf-8'))
    for r in records: financials.validate(r)
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if activation.target_identity(connection)!=state['target'] or activation.digest(activation.catalog(connection,True))!=state['earnings_schema_signature'] or activation.digest(activation.catalog(connection,False))!=state['macro_schema_signature']:
            raise ValueError('Target/schema changed during preflight')
        periods=[]
        for r in records:
            if not connection.execute('SELECT 1 FROM earnings_companies WHERE company_id=%s AND cik=%s AND ticker=%s',
                (financials.identity(r['cik']),r['cik'],r['ticker'])).fetchone():
                raise ValueError('Proposed facts require the existing verified pilot company')
            period=financials.identity(f"{r['cik']}:{r['fiscal_year']}:{r['fiscal_quarter']}")
            existing=connection.execute('SELECT period_label,period_end FROM earnings_periods WHERE period_id=%s',(period,)).fetchone()
            if existing and (existing[0],str(existing[1]))!=(r['period_label'],r['period_end']):
                raise ValueError('Stored E2A period conflicts with proposed financial facts')
            periods.append({'period_id':period,'label':r['period_label'],'ticker':r['ticker'],'create':existing is None})
    return dict(proposal_version=1,prepared_at=datetime.now(timezone.utc).isoformat(),
        status='proposal_only_requires_fresh_backup_restore_test_and_explicit_approval',
        ready_for_apply=False,preflight=state,
        artifacts={p:activation.file_hash(financials.ROOT/p) for p in FILES},
        ddl_tables=['earnings_financial_documents','earnings_financial_observations'],
        ddl_function='earnings_financial_guard',ddl_triggers=4,
        manual_documents=len(records),manual_observations=sum(len(r['observations']) for r in records),
        periods=periods,new_events=sum(p['create'] for p in periods),
        preserved='All existing macro rows and E2A rows; append historical periods/events only',
        backup='Fresh full custom pg_dump of this exact target; checksum and successful isolated restore required before approval',
        rollback='One transaction rolls back DDL and seed; post-commit financial-only removal requires separate approval and dependency review')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with get_independent_connection() as connection: plan=prepare(connection,args.target)
    args.output.write_text(json.dumps(plan,default=str,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':plan['status'],'proposal_sha256':activation.digest(plan),'ready_for_apply':False}))


if __name__=='__main__': main()
