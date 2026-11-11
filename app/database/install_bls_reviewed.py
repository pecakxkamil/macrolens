"""Install exact approved delivery after DB revision verify; no database writes.

Use only during the agreed service window. Never stops a process itself.
Existing token and old bytes are retained in the owned deployment archive.
"""
import argparse,hashlib,json,os,socket,tempfile
from pathlib import Path

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def filehash(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('root','source','plan','receipt','archive'):parser.add_argument('--'+name,type=Path,required=True)
 parser.add_argument('--confirm-plan',required=True);args=parser.parse_args()
 root=args.root.resolve();source=args.source.resolve();archive=args.archive.resolve()
 plan=json.loads(args.plan.read_text(encoding='utf-8'));receipt=json.loads(args.receipt.read_text(encoding='utf-8'))
 if digest(plan)!=args.confirm_plan or receipt['outcome']!='verified' or receipt['plan_sha256']!=args.confirm_plan:raise ValueError('Verified approved revision required')
 token=receipt['runtime_token']
 if token['target']!=plan['target'] or token['artifacts']!=plan['artifacts'] or token.get('version')!=3 or token['plan_sha256']!=args.confirm_plan:raise ValueError('Wrong runtime token')
 if root==Path('C:/Projects/macrolens').resolve():
  for port in (8000,5173):
   with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1',port))==0:raise ValueError('Normal API/Vite must be stopped in the agreed window')
 if root==source or archive==root or root in archive.parents and 'data' not in archive.relative_to(root).parts:raise ValueError('Unsafe deployment archive')
 for item in plan['delivery']:
  rel=Path(item['path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe delivery path')
  if filehash(source/rel)!=item['after'] or filehash(root/rel) not in (item['before'],item['after']):raise ValueError('Delivery/source base changed: '+str(rel))
 archive.mkdir(parents=True,exist_ok=True)
 for item in plan['delivery']:
  rel=Path(item['path']);dest=root/rel;old=archive/'before'/rel
  if dest.exists() and filehash(dest)!=item['after']:
   old.parent.mkdir(parents=True,exist_ok=True)
   if old.exists():
    if filehash(old)!=item['before']:raise ValueError('Deployment archive conflict')
   else:
    with old.open('xb') as stream:stream.write(dest.read_bytes())
  dest.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as stream:
   stream.write((source/rel).read_bytes());temp=stream.name
  os.replace(temp,dest)
 tokenpath=root/'data/raw/forecast-f1/activation.json'
 tokenpath.parent.mkdir(parents=True,exist_ok=True)
 if tokenpath.exists():
  old=archive/'original-runtime-token.json'
  if not old.exists():
   with old.open('xb') as stream:stream.write(tokenpath.read_bytes())
 with tempfile.NamedTemporaryFile(dir=tokenpath.parent,delete=False) as stream:
  stream.write(json.dumps(token,indent=2).encode());temp=stream.name
 os.replace(temp,tokenpath)
 print('Exact delivery and verified BLS V3 token installed; services remain stopped')

if __name__=='__main__':main()
