"""Exact V5 file cutover/rollback after separate DB verification; no SQL or restart."""
import argparse,hashlib,json,os,socket,tempfile
from pathlib import Path
from app.database.forecast_f1_authorization_financial import DELIVERY_PATHS

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def filehash(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def atomic(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:f.write(raw);name=f.name
 os.replace(name,path)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('root','source','plan','receipt','archive'):parser.add_argument('--'+name,type=Path,required=True)
 parser.add_argument('--confirm-plan',required=True);parser.add_argument('--rollback',action='store_true');a=parser.parse_args()
 root=a.root.resolve();source=a.source.resolve();archive=a.archive.resolve();p=json.loads(a.plan.read_text());receipt=json.loads(a.receipt.read_text());h=digest(p)
 if h!=a.confirm_plan or receipt['outcome']!='verified' or receipt['plan_sha256']!=h:raise ValueError('Exact verified plan/receipt required')
 token=receipt['runtime_token']
 if token!=dict(version=5,plan_sha256=h,target=p['target'],artifacts=p['artifacts']):raise ValueError('Wrong V5 receipt')
 if [d['path'] for d in p['delivery']]!=list(DELIVERY_PATHS):raise ValueError('Exact reviewed delivery required')
 if root==source or archive==root or archive==source or root in archive.parents and 'data' not in archive.relative_to(root).parts:raise ValueError('Unsafe archive/source')
 if root==Path('C:/Projects/macrolens').resolve():
  for port in (8000,5173):
   with socket.socket() as sock:
    if sock.connect_ex(('127.0.0.1',port))==0:raise ValueError('Normal API/Vite must be stopped in the separately approved window')
 for d in p['delivery']:
  rel=Path(d['path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe path')
  if filehash(root/rel) not in (d['before'],d['after']):raise ValueError('Target bytes changed: '+str(rel))
 tokenpath=root/'data/raw/forecast-f1/activation.json';recordpath=archive/'installation.json';oldtoken=archive/'original-runtime-token.json'
 if a.rollback:
  record=json.loads(recordpath.read_text())
  if record['plan_sha256']!=h:raise ValueError('Wrong installation archive')
  current=json.loads(tokenpath.read_text()) if tokenpath.is_file() else None
  old=json.loads(oldtoken.read_text()) if oldtoken.is_file() else None
  if current not in (token,old):raise ValueError('Runtime token changed after install')
  for d in p['delivery']:
   rel=Path(d['path']);saved=archive/'before'/rel
   if d['before'] is not None and d['before']!=d['after'] and filehash(saved)!=d['before']:raise ValueError('Original archive missing/changed')
  for d in p['delivery']:
   rel=Path(d['path']);dest=root/rel
   if filehash(dest)==d['before']:continue
   if d['before'] is None:dest.unlink()
   else:atomic(dest,(archive/'before'/rel).read_bytes())
  if record['original_token_present']:atomic(tokenpath,oldtoken.read_bytes())
  elif tokenpath.exists():tokenpath.unlink()
  print('Exact previous bytes/token restored; append-only DB revision retained; services remain stopped');return
 for d in p['delivery']:
  if filehash(source/d['path'])!=d['after']:raise ValueError('Source delivery changed')
 archive.mkdir(parents=True,exist_ok=True)
 if recordpath.exists():
  record=json.loads(recordpath.read_text())
  if record['plan_sha256']!=h:raise ValueError('Archive belongs to another plan')
 else:
  record=dict(plan_sha256=h,original_token_present=tokenpath.is_file())
  if tokenpath.is_file():
   if oldtoken.exists():raise ValueError('Archive already contains a foreign token')
   with oldtoken.open('xb') as f:f.write(tokenpath.read_bytes())
  with recordpath.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
 for d in p['delivery']:
  rel=Path(d['path']);dest=root/rel;saved=archive/'before'/rel
  if filehash(dest)==d['after']:continue
  if dest.is_file():
   saved.parent.mkdir(parents=True,exist_ok=True)
   if saved.exists():
    if filehash(saved)!=d['before']:raise ValueError('Archive conflict')
   else:
    with saved.open('xb') as f:f.write(dest.read_bytes())
  atomic(dest,(source/rel).read_bytes())
 if any(filehash(root/d['path'])!=d['after'] for d in p['delivery']):raise ValueError('Installed file hash mismatch; token not switched')
 atomic(tokenpath,json.dumps(token,indent=2).encode())
 print('Exact verified V5 delivery/token installed; no SQL; services remain stopped')

if __name__=='__main__':main()
