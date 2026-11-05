"""Isolated F1 refresh, dispatched via existing MacroLens task launcher.

Normal writes require a separate immutable policy/token. No second scheduler.
"""
import json
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import httpx
from psycopg.types.json import Jsonb
from app import forecast_f1 as f
from app.forecast_f1_sources import fetch_cleveland

LOCK=726530031

def run(factory,directory,macro_events=(),earnings_events=(),transport=None,authorization=None,events_loader=None):
 def check(c):
  if authorization is None:f.isolated(c)
  else:
   from app.database.activate_forecast_f1 import authorized
   with c.transaction():
    c.execute('SET TRANSACTION READ ONLY');authorized(c,authorization)
 def approve_records(records):
  if authorization is None:return
  from app.database.activate_forecast_f1 import seed
  allowed={f.digest(r['subject']) for r in seed() if r['kind']=='model_nowcast'}
  if not records or any(r['kind']!='model_nowcast' or r['source_id']!='cleveland-inflation' or r['source_url']!='https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting' or f.digest(r['subject']) not in allowed for r in records):raise ValueError('Outside approved F1 dispatch scope')

 with factory() as lease:
  check(lease);lease.autocommit=True
  if not lease.execute('SELECT pg_try_advisory_lock(%s)',(LOCK,)).fetchone()[0]:return dict(status='busy',added=0)
  try:
   now=datetime.now(timezone.utc)
   latest=lease.execute("SELECT retry_at FROM forecast_refresh_checks WHERE source_id='cleveland-inflation' ORDER BY checked_at DESC LIMIT 1").fetchone()
   added=0;status='cooldown'
   if not latest or latest[0]<=now:
    # Commit a durable claim BEFORE HTTP. A crash cannot trigger another
    # publisher attempt on restart inside the same 24h window.
    with factory() as c:
     check(c)
     c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
     c.execute('INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,%s,%s,%s,%s)',(uuid4(),'cleveland-inflation','not_modified',now+timedelta(days=1),Jsonb(dict(kind='attempt_started'))))
    try:
     if authorization is None:records,receipt=fetch_cleveland(directory,transport)
     else:
      from app.database.activate_forecast_f1 import policy
      records,receipt=fetch_cleveland(directory,transport,policy()['terms_section_sha256'])
     approve_records(records)
     with factory() as c:
      check(c)
      c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
      added=f.append(c,records) if authorization is None else f._append_prepared(c,records)
     status='success';detail=receipt;retry=now+timedelta(days=1)
    except Exception as error:
     status='blocked' if isinstance(error,ValueError) else 'error';detail=dict(error_type=type(error).__name__);retry=now+timedelta(hours=1)
     if isinstance(error,httpx.HTTPStatusError):
      detail['http_status']=error.response.status_code
      if error.response.status_code in (403,401):status='blocked';retry=now+timedelta(days=1)
      if error.response.status_code==429:
       raw=error.response.headers.get('retry-after','3600')
       try:seconds=int(raw)
       except ValueError:
        from email.utils import parsedate_to_datetime
        try:seconds=int((parsedate_to_datetime(raw)-now).total_seconds())
        except (TypeError,ValueError):seconds=3600
       retry=now+timedelta(seconds=max(60,min(seconds,86400)))
    # At most one control attempt per 24h, including failed requests.
    retry=max(retry,now+timedelta(days=1))
    with factory() as c:
     check(c);c.execute('INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,%s,%s,%s,%s)',(uuid4(),'cleveland-inflation',status,retry,Jsonb(detail)))
   # Freeze is a worker operation, never a Calendar GET side effect.
   frozen=0
   with factory() as c:
    check(c)
    if events_loader:
     with c.transaction():
      c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
      macro_events,earnings_events=events_loader(c)
    c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
    existing=f.load(c)
    subjects={v['subject_key'] for v in existing[0]}
    freeze=f.freeze if authorization is None else f._freeze_prepared
    for e in macro_events:
     for m in e.get('measures',[]):
      subject=f.macro_subject(m,e)
      if subject and f.digest(subject) in subjects and m.get('actual') is not None and e.get('release_datetime_utc'):
       frozen+=freeze(c,e['event_id'],subject,f.instant(e['release_datetime_utc']))
    for e in earnings_events:
     if e.get('publication_state',{}).get('code','').startswith('published') and f.earnings_cutoff(e):
      for metric in ('revenue','reported_diluted_eps'):
       subject=f.earnings_subject(e,metric)
       if subject and f.digest(subject) in subjects:frozen+=freeze(c,e['event_id'],subject,f.earnings_cutoff(e))
   return dict(status=status,added=added,frozen=frozen)
  finally:lease.execute('SELECT pg_advisory_unlock(%s)',(LOCK,))

def dispatch(factory,directory,**kwargs):
 # The caller is the existing coordinator; no new loop/timer/process is created.
 # Validate target before dispatch or publisher HTTP. No normal activation path.
 with factory() as c:f.isolated(c)
 from app.analytics.overview_refresh import coordinator
 return coordinator.launch(lambda:run(factory,directory,**kwargs))
