"""Durable bounded Earnings checks; never called by Calendar GET.

Network checks need a separately approved activation policy and matching local
runtime token. Ordinary normal databases without those gates are read-only.
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from app.database.connection import get_independent_connection
from app.database.activate_earnings_history_v2 import schema_state
from app.database import activate_earnings as base
from app import earnings, earnings_reports as reports
from app import earnings_monitor_policy as policy, earnings_monitor_sources as sources
from app.ingestion.request_budget import request_budget

ROOT = Path(__file__).resolve().parents[1]
TOKEN = Path(os.environ.get('EARNINGS_MONITOR_TOKEN', str(ROOT / 'data/raw/earnings-monitor/activation.json')))
RAW = ROOT / 'data/raw/earnings-monitor/documents'
LOCK = 726530022
SCHEMA = ROOT / 'app/database/earnings_monitor_schema.sql'
logger = logging.getLogger(__name__)
ARTIFACTS = ('app/earnings_monitor.py','app/earnings_monitor_policy.py','app/earnings_monitor_sources.py',
             'app/earnings_monitor_runtime.py','app/earnings_reports.py','app/earnings.py','app/earnings_session.py',
             'config/earnings_monitor_sources.json','config/earnings_companies_reviewed.json',
             'app/database/earnings_monitor_schema.sql','app/database/activate_earnings_monitor.py',
             'app/database/earnings_report_schema.sql','app/database/activate_earnings_history_v2.py',
             'app/database/activate_earnings.py','app/ingestion/request_budget.py','app/database/connection.py')


def artifacts():
    import pypdf
    return {**{p:base.file_hash(ROOT/p) for p in ARTIFACTS},
            'pypdf_version':pypdf.__version__,'httpx_version':httpx.__version__}


def utc_now():
    return datetime.now(timezone.utc)


def authorized(connection, token):
    if (set(token) != {'plan_sha256','target','artifacts'} or token['artifacts'] != artifacts()
        or token['artifacts'] != IMPORTED_ARTIFACTS):
        raise ValueError('Monitor activation artifacts changed')
    if base.target_identity(connection) != token['target'] or not 170000 <= connection.info.server_version < 180000:
        raise ValueError('Monitor target changed')
    if not all(connection.execute("SELECT to_regclass('earnings_monitor_policy'),to_regclass('earnings_report_checks')").fetchone()):
        raise ValueError('Monitor store not activated')
    row = connection.execute('SELECT approved_plan_sha256,target,artifacts,schema_sha256 FROM earnings_monitor_policy WHERE id=1').fetchone()
    if not row or row[:3] != (token['plan_sha256'],token['target'],token['artifacts']) or row[3] != base.digest(schema_state(connection)):
        raise ValueError('Monitor runtime token/policy mismatch')


def history(connection, event_id):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute('SELECT * FROM earnings_report_checks WHERE event_id=%s ORDER BY scheduled_for,phase', (event_id,))
        return cursor.fetchall()


def audit(connection, check_id, event_id, slot, now, phase, status, detail, retry_after=None):
    connection.execute('''INSERT INTO earnings_report_checks
      (check_id,phase,event_id,scheduled_for,attempted_at,finished_at,status,retry_after,detail)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
      (check_id,phase,event_id,slot,now,now if phase=='result' else None,status,retry_after,
       Jsonb(detail)))


def run(connection_factory=get_independent_connection, token=None, clock=utc_now, transport=None, directory=RAW, cancelled=lambda:False):
    if token is None:
        if not TOKEN.exists():
            return dict(status='awaiting_activation',checked=0)
        token = json.loads(TOKEN.read_text(encoding='utf-8'))
    with connection_factory() as lease:
        lease.autocommit = True
        # Verify authorization read-only before ever acquiring a writing connection.
        with lease.transaction():
            lease.execute('SET TRANSACTION READ ONLY')
            authorized(lease, token)
        if not lease.execute('SELECT pg_try_advisory_lock(%s)',(LOCK,)).fetchone()[0]:
            return dict(status='busy',checked=0)
        checked = 0
        try:
            with lease.transaction():
                lease.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                events = earnings.load_events(lease)
            last_request = [0.0]
            def pace(url):
                if cancelled():
                    raise sources.ReviewRequired('shutdown_before_request')
                delay=max(0, last_request[0]+1-time.monotonic())
                if delay:
                    time.sleep(delay)
                last_request[0]=time.monotonic()
            with request_budget(seconds=240), httpx.Client(timeout=25,follow_redirects=False,transport=transport,trust_env=False,
                    headers={'User-Agent':'MacroLens/0.1 (local earnings research; public IR)'}) as client:
                for event in events:
                    if cancelled():
                        break
                    event_id=event['event_id'][len('earnings:'):]
                    now=clock()
                    with lease.transaction():
                        lease.execute('SET TRANSACTION READ ONLY')
                        attempts=history(lease,event_id)
                    # An abandoned durable claim is closed after the maximum fetch budget;
                    # restart then coalesces to the latest slot, never replays missed slots.
                    for row in attempts:
                        if (row['phase']=='started' and not any(r['check_id']==row['check_id'] and r['phase']=='result' for r in attempts)
                            and row['attempted_at']+timedelta(minutes=5)<now):
                            with lease.transaction():
                                recovery=policy.schedule(event)
                                expired=recovery is not None and now>=recovery['end']
                                audit(lease,row['check_id'],event_id,row['scheduled_for'],now,'result',
                                      'review_required' if expired else 'interrupted',
                                      {'reason':'48_hour_window_expired_after_restart' if expired else 'worker_restart'})
                    selected=policy.due(event,now,attempts)
                    if selected is None:
                        continue
                    check_id=earnings.identity('monitor:'+event_id+':'+selected['slot'].isoformat())
                    with lease.transaction():
                        authorized(lease,token)
                        audit(lease,check_id,event_id,selected['slot'],now,'started','started',{'window':selected['window']})
                    checked+=1
                    spec=sources.binding(event)
                    status,detail,retry_after='review_required',{},None
                    record=None
                    try:
                        if selected['expired']:
                            detail={'reason':'48_hour_window_expired'}
                        elif spec is None:
                            detail={'reason':'publisher_adapter_not_reviewed'}
                        else:
                            body,receipt=sources.fetch(client,spec,directory,now,pace)
                            record=sources.parse(body,spec,receipt)
                            status,detail='imported',{'receipt':receipt,'parser':sources.PARSER_VERSION}
                    except sources.NotPublished as error:
                        status,detail='not_found',{'reason':str(error)}
                    except sources.RetryHTTP as error:
                        failures=sum(r['status']=='http_retry' for r in attempts)
                        wait=max(error.retry_after,min(7200,900*2**min(failures,3)))
                        status,detail,retry_after='http_retry',{'reason':str(error)},now+timedelta(seconds=wait)
                    except (httpx.TimeoutException,httpx.NetworkError) as error:
                        status,detail,retry_after='http_retry',{'reason':type(error).__name__},now+timedelta(minutes=15)
                    except sources.ReviewRequired as error:
                        status,detail='review_required',{'reason':str(error)}
                    except Exception as error:
                        status,detail='review_required',{'reason':'validation_failed','error_type':type(error).__name__}
                    if cancelled():
                        status,detail,record='interrupted',{'reason':'worker_shutdown'},None
                    try:
                        with lease.transaction():
                            lease.execute("SET LOCAL lock_timeout='5s'")
                            lease.execute("SET LOCAL statement_timeout='120s'")
                            authorized(lease,token)
                            if record is not None:
                                # Identity/current-version checks are inside the original E2D writer.
                                # A newly published/current report is never silently overwritten.
                                lease.execute('SELECT pg_advisory_xact_lock(726530020)')
                                latest=lease.execute('SELECT document_type,source_version FROM earnings_report_documents WHERE event_id=%s ORDER BY version DESC LIMIT 1',(event_id,)).fetchone()
                                if latest and latest[0]=='earnings_release':
                                    if latest[1]!=record['document']['source_version']:
                                        raise ValueError('Report changed; reviewed correction required')
                                else:
                                    reports._append_prepared(lease,[record])
                                latest_id=lease.execute('SELECT document_id FROM earnings_report_documents WHERE event_id=%s ORDER BY version DESC LIMIT 1',(event_id,)).fetchone()[0]
                                actual=dict(lease.execute('SELECT metric,actual FROM earnings_report_observations WHERE document_id=%s',(latest_id,)).fetchall())
                                expected={v['metric']:reports.Decimal(v['source_value'])*reports.SCALES[v['source_unit']] for v in record['observations']}
                                if actual!=expected or len(actual)!=2:raise ValueError('Imported metric snapshot mismatch')
                            audit(lease,check_id,event_id,selected['slot'],clock(),'result',status,detail,retry_after)
                    except Exception as error:
                        status='review_required'
                        with lease.transaction():
                            audit(lease,check_id,event_id,selected['slot'],clock(),'result','review_required',{'reason':'atomic_import_rejected','error_type':type(error).__name__})
                    logger.info('earnings check event=%s slot=%s status=%s',event_id,selected['slot'].isoformat(),status)
            return dict(status='completed',checked=checked)
        finally:
            lease.execute('SELECT pg_advisory_unlock(%s)',(LOCK,))


# Prevent an old worker from accepting hashes of files replaced after its import.
IMPORTED_ARTIFACTS = artifacts()
