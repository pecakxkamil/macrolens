"""Explicit owned-clone V5 trial. Never accepts a normal database connection."""
import os,sys,json,copy,hashlib,subprocess,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from app.database import forecast_f1_authorization_financial as a
from app import forecast_f1 as model
from app.database.connection import shared_connection

def main():
 stage=Path(os.environ['FINANCIAL_TRIAL_STAGE']).resolve();cfg=json.loads((stage/'clone.json').read_text());w=json.loads((stage/'workspace.json').read_text());root=Path(w['root']);r=Path(w['candidate'])
 assert cfg['params']['host']=='127.0.0.1' and cfg['params']['port']==55554 and cfg['params']['user']=='macrolens_ci' and cfg['name'].startswith('macrolens_forecast_f1_ui_')
 info=json.loads(subprocess.check_output(['docker','inspect',cfg['container']]))[0]
 assert info['Id']==cfg['container'] and info['Config']['Labels']['task']=='macrolens-financial-v5-2026-11-12'
 params={**cfg['params'],'dbname':cfg['name']};factory=lambda:psycopg.connect(**params)
 backup=json.loads((stage/'clone-backup.json').read_text());delivery=json.loads((stage/'delivery.json').read_text());checks=[]
 def passed(name):checks.append(name);print(name,flush=True)
 with factory() as c:
  c.read_only=True;before=a.v4.v3.financial.table_snapshots(c);oldrows=c.execute('SELECT row_to_json(t)::text FROM forecast_refresh_checks t ORDER BY check_id').fetchall()
 with factory() as c:c.read_only=True;p=a.prepare(c,delivery,backup,test_only=True)
 h=model.digest(p);(stage/'clone-plan.json').write_text(json.dumps(p,indent=2))
 with factory() as c:
  try:a.apply(c,p,a.v4.v3.base.target_label(p['target']),h,backup,fail_after_insert=True)
  except psycopg.errors.DivisionByZero:pass
  else:raise AssertionError('Rollback injection absent')
 with factory() as c:assert a.v4.v3.financial.table_snapshots(c)==before
 passed('injected rollback preserves all 29 table fingerprints')
 def reject(label,callback):
  try:callback()
  except ValueError:passed(label);return
  raise AssertionError('Expected rejection: '+label)
 with factory() as c:reject('wrong explicit plan hash rejected',lambda:a.apply(c,p,a.v4.v3.base.target_label(p['target']),'0'*64,backup))
 with psycopg.connect(**cfg['params'],dbname='macrolens_ci') as c:reject('wrong real database rejected before any revision write',lambda:a.apply(c,p,a.v4.v3.base.target_label(p['target']),h,backup))
 changed=copy.deepcopy(p);changed['artifacts']['app/analytics/calendar_readings.py']='0'*64
 with factory() as c:reject('changed artifact map rejected',lambda:a.apply(c,changed,a.v4.v3.base.target_label(p['target']),model.digest(changed),backup))
 path=r/'app/analytics/calendar_readings.py';original=path.read_bytes()
 try:
  path.write_bytes(original+b'\n')
  with factory() as c:reject('changed actual source bytes rejected',lambda:a.apply(c,p,a.v4.v3.base.target_label(p['target']),h,backup))
 finally:path.write_bytes(original)
 changed=copy.deepcopy(p);changed['predecessor']['plan_sha256']='0'*64
 with factory() as c:reject('changed predecessor rejected',lambda:a.apply(c,changed,a.v4.v3.base.target_label(p['target']),model.digest(changed),backup))
 changed=copy.deepcopy(p);changed['protected']['forecast_vintages']['sha256']='0'*64
 with factory() as c:reject('stale forecast snapshot rejected',lambda:a.apply(c,changed,a.v4.v3.base.target_label(p['target']),model.digest(changed),backup))
 with factory() as c:assert a.v4.v3.financial.table_snapshots(c)==before
 with factory() as c:assert a.apply(c,p,a.v4.v3.base.target_label(p['target']),h,backup)['outcome']=='created'
 with factory() as c:after=a.v4.v3.financial.table_snapshots(c);rows=c.execute('SELECT row_to_json(t)::text FROM forecast_refresh_checks t WHERE source_id<>%s ORDER BY check_id',(a.SOURCE,)).fetchall();assert rows==oldrows
 assert {k:v for k,v in before.items() if k!='forecast_refresh_checks'}=={k:v for k,v in after.items() if k!='forecast_refresh_checks'}
 assert after['forecast_refresh_checks']['rows']==before['forecast_refresh_checks']['rows']+1
 passed('one revision INSERT only; all old rows and all other table fingerprints unchanged')
 with factory() as c:assert a.apply(c,p,a.v4.v3.base.target_label(p['target']),h,backup)['outcome']=='already_initialized'
 with factory() as c:assert a.v4.v3.financial.table_snapshots(c)==after
 with factory() as c:receipt=a.verify(c,p)
 passed('idempotence leaves all table bytes unchanged; V5 token verified on owned clone only')
 receiptpath=stage/'clone-verified.json';receiptpath.write_text(json.dumps(receipt,indent=2))
 # Every public authorization entry point must preserve V5 without bypassing it.
 with factory() as c:
  for entry in (a.v4.v3.legacy.authorized,a.v4.v3.authorized,a.v4.authorized):assert entry(c,receipt['runtime_token'])==p
 passed('F1, Employment and CPI authorization dispatch all validate the complete V5 chain')
 with factory() as c:
  c.read_only=True
  q=c.execute("SELECT observation_date,value FROM observation_vintages WHERE series_id='PAYEMS' AND source='alfred' AND vintage_date='2026-10-02' AND observation_date IN ('2026-08-01','2026-09-01') ORDER BY observation_date").fetchall();assert q[1][1]-q[0][1]==29
  from app.analytics.calendar_agenda import calendar_agenda
  from datetime import date
  with shared_connection(c):events=calendar_agenda(date(2026,11,5),date(2026,11,10))['events']
  rows={(str(e['release_date']),m['series_id'],m['feature_name']):m for e in events for m in e.get('measures',[])}
  for sid,pair in {'DFF':(3.88,3.88),'DGS2':(4.56,4.51),'DGS10':(4.88,4.86),'DFII10':(2.66,2.63)}.items():assert (rows[('2026-11-10',sid,'raw')]['actual'],rows[('2026-11-10',sid,'raw')]['previous'])==pair
  assert rows[('2026-11-05','MORTGAGE30US','raw')]['actual']==7.18
 passed('real SQL/API binding returns five pairs; historical ALFRED NFP first print remains 29')
 # Exact file install, rollback to original normal bytes, then reinstall, all in Temp.
 deploy=Path(w['parent'])/'cutover';shutil.copytree(r,deploy,ignore=shutil.ignore_patterns('node_modules','dist','__pycache__'))
 for d in delivery:
  dest=deploy/d['path']
  if d['before'] is None:
   if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==d['after'];dest.unlink()
  else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((root/d['path']).read_bytes())
 tokenpath=deploy/'data/raw/forecast-f1/activation.json';tokenpath.parent.mkdir(parents=True,exist_ok=True);oldtoken=(root/'data/raw/forecast-f1/activation.json').read_bytes();tokenpath.write_bytes(oldtoken)
 archive=Path(w['parent'])/'cutover-archive';cmd=[sys.executable,'-m','app.database.install_financial_reviewed','--root',str(deploy),'--source',str(r),'--plan',str(stage/'clone-plan.json'),'--receipt',str(receiptpath),'--archive',str(archive),'--confirm-plan',h]
 def install(extra=()):
  result=subprocess.run(cmd+list(extra),cwd=r,capture_output=True,env=dict(os.environ,PYTHON_DOTENV_DISABLED='1'));assert result.returncode==0,result.stderr.decode(errors='replace')
 install();assert json.loads(tokenpath.read_text())==receipt['runtime_token'];install();install(['--rollback'])
 assert tokenpath.read_bytes()==oldtoken
 for d in delivery:assert (hashlib.sha256((deploy/d['path']).read_bytes()).hexdigest() if (deploy/d['path']).is_file() else None)==d['before']
 install();assert all(hashlib.sha256((deploy/d['path']).read_bytes()).hexdigest()==d['after'] for d in delivery)
 w['deployed']=str(deploy);(stage/'workspace.json').write_text(json.dumps(w,indent=2));passed('file cutover idempotence, exact V4 byte/token rollback and V5 reinstall passed in isolated root')
 (stage/'clone-validation.json').write_text(json.dumps(dict(passed=checks,plan_sha256=h,artifacts=len(p['artifacts']),preserved_tables=len(before)-1,old_check_rows_preserved=len(oldrows),sql_inserted_rows=1),indent=2))

if __name__=='__main__':main()
