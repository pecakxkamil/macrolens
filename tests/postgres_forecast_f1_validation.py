"""Owned PG17 F1 validation. Synthetic temporal cases are never pilot data."""
import copy
import json
import os
import subprocess
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from app import forecast_f1 as f
from app import forecast_f1_refresh as refresh
from tests.postgres_http_guard import no_publisher_http
from tests.test_forecast_f1 import record


def main():
 if os.environ.get('DB_NAME')!='macrolens_forecast_f1_control' or os.environ.get('DB_HOST') not in ('localhost','127.0.0.1'):raise ValueError('Owned loopback F1 control required')
 params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
 if len(sys.argv)>1:
  name=sys.argv[1]
  assert name.startswith(f.PREFIX)
  assert refresh.run(lambda:psycopg.connect(**params,dbname=name),Path('.'))['status']=='busy';print('busy without HTTP');return
 with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
  name=f.PREFIX+'validation_'+uuid4().hex[:12];admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
  factory=lambda:psycopg.connect(**params,dbname=name)
  try:
   with factory() as c:
    c.execute('CREATE TABLE earnings_companies(company_id uuid PRIMARY KEY,cik text NOT NULL)')
    reviewed=json.loads((f.ROOT/'config/forecast_f1_reviewed.json').read_text())
    for b in reviewed['earnings_basis'].values():c.execute('INSERT INTO earnings_companies VALUES(%s,%s)',(b['company_id'],b['cik']))
   with factory() as c:
    try:
     with c.transaction():f.initialize(c);c.execute('SELECT 1/0')
    except psycopg.errors.DivisionByZero:pass
    assert c.execute("SELECT to_regclass('forecast_vintages')").fetchone()[0] is None;c.rollback()
    f.initialize(c)
   synthetic=record()
   with factory() as c:
    assert f.append(c,[synthetic])==1;assert f.append(c,[synthetic])==0
    assert f.append(c,reviewed['earnings_records'])==4
   with factory() as c:
    c.read_only=True;store=f.load(c);assert len(store[0])==5
    captured=next(x for x in store[0] if x['payload']['kind']=='model_nowcast')['captured_at'];c.rollback()
   cutoff=datetime.now(timezone.utc)
   with factory() as c:
    assert f.freeze(c,'synthetic:e',synthetic['subject'],cutoff)
    assert not f.freeze(c,'synthetic:e',synthetic['subject'],cutoff)
    missing=copy.deepcopy(synthetic['subject']);missing['period']='2026-09-01'
    assert f.freeze(c,'synthetic:missing',missing,cutoff)
   changed=copy.deepcopy(synthetic);changed['value']='0.30'
   with factory() as c:
    assert f.append(c,[changed])==1
    try:
     with c.transaction():f.append(c,[synthetic])
    except ValueError:pass
    else:raise AssertionError('Stale forecast reactivated')
   with factory() as c:
    c.read_only=True;store=f.load(c)
    chosen,state=f.choose(store,synthetic['subject'],'synthetic:e',cutoff,True)
    assert chosen['value']=='0.24' and state=='frozen'
    assert f.choose(store,missing,'synthetic:missing',cutoff,True)[0] is None
    assert f.choose(store,synthetic['subject'],'published-without-freeze',cutoff,True)[1]=='freeze_pending'
   for command in ['UPDATE forecast_vintages SET version=2','DELETE FROM forecast_freezes','TRUNCATE forecast_refresh_checks']:
    with factory() as c:
     try:
      with c.transaction():c.execute(command)
     except psycopg.Error:pass
     else:raise AssertionError('Mutable history')
   with factory() as c:
    bad=copy.deepcopy(changed);bad['value']='0.31';bad['subject']['adjustment']='bad'
    try:
     with c.transaction():c.execute('INSERT INTO forecast_vintages(forecast_id,subject_key,kind,source_id,version,fingerprint,payload) VALUES(%s,%s,%s,%s,%s,%s,%s)',(uuid4(),f.digest(bad['subject']),bad['kind'],bad['source_id'],1,f.digest(bad),Jsonb(bad)))
    except psycopg.Error:pass
    else:raise AssertionError('SQL semantic bypass')
   # Another OS process sees the same SQL lease, no transport invoked.
   with factory() as c:
    c.execute('SELECT pg_advisory_lock(%s)',(refresh.LOCK,));c.commit()
    probe=subprocess.run([sys.executable,__file__,name],capture_output=True,text=True,env=os.environ)
    assert probe.returncode==0,probe.stdout+probe.stderr
    c.execute('SELECT pg_advisory_unlock(%s)',(refresh.LOCK,));c.commit()
   # Two simultaneous importers serialize on subject; only one new version.
   import threading
   results=[];errors=[];revision=copy.deepcopy(changed);revision['value']='0.32'
   def append():
    try:
     with factory() as c:results.append(f.append(c,[revision]))
    except BaseException as e:errors.append(e)
   threads=[threading.Thread(target=append) for _ in range(2)]
   for t in threads:t.start()
   for t in threads:t.join(10);assert not t.is_alive()
   assert not errors and sorted(results)==[0,1]
   # Durable HTTP backoff survives a new invocation; no hidden retry in GET.
   import httpx
   calls=[]
   def rate_limited(request):
    calls.append(str(request.url))
    if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nAllow: /')
    return httpx.Response(429,headers={'Retry-After':'7200'})
   from tempfile import TemporaryDirectory
   with TemporaryDirectory() as directory:
    outcome=refresh.run(factory,directory,transport=httpx.MockTransport(rate_limited))
    assert outcome['status']=='error' and outcome['added']==0
    count=len(calls)
    assert refresh.run(factory,directory,transport=httpx.MockTransport(rate_limited))['status']=='cooldown'
    assert len(calls)==count
    with factory() as c:
     row=c.execute("SELECT retry_at,checked_at,detail FROM forecast_refresh_checks ORDER BY checked_at DESC LIMIT 1").fetchone()
     assert (row[0]-row[1]).total_seconds()>7100 and row[2]['http_status']==429
   print('F1 PG17 PASSED: atomic DDL rollback, real SQL append-only/version/idempotency, null and pre-release freezes, no backfill, stale version rejection, semantic guards, two processes and concurrent writers; synthetic temporal tests separately labelled')
  finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))

if __name__=='__main__':
 with no_publisher_http():main()
