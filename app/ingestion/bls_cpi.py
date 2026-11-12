"""Source-specific CPI SA/NSA captures. Anonymous levels are never published rates."""
import copy
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL
from html.parser import HTMLParser
import httpx
from psycopg.types.json import Jsonb
from app.ingestion import bls_budget as budget
from app.ingestion.bls_employment import URL, instant, retry_after, MAX_BYTES

SOURCE='bls:cpi'
CONTRACT={
 'CPIAUCSL:mom':('CUSR0000SA0','SA','mom'),
 'CPILFESL:mom':('CUSR0000SA0L1E','SA','mom'),
 'CPIAUCSL:yoy':('CUUR0000SA0','NSA','yoy'),
 'CPILFESL:yoy':('CUUR0000SA0L1E','NSA','yoy'),
}
POLICY=dict(version=1,release_id=10,source=SOURCE,series=CONTRACT,url=URL,
 window_seconds=172800,catch_up='48h from confirmed release; no history replay',
 account_limit=budget.LIMIT,interval_seconds=budget.INTERVAL,
 storage='publisher_documents only; no FRED/ALFRED overwrite',precision=1,
 method='derived_from_bls_levels_rounded_1dp',timeout_seconds=25,max_bytes=MAX_BYTES)


def month(value,offset=0):
 d=date.fromisoformat(value)
 if d.day!=1:raise ValueError('Month must start on day one')
 n=d.year*12+d.month-1+offset
 return str(date(n//12,n%12+1,1))


def unique(pairs):
 result={}
 for k,v in pairs:
  if k in result:raise ValueError('Duplicate JSON key')
  result[k]=v
 return result


def parse(raw,period):
 observed=date.fromisoformat(month(period));p=json.loads(raw,object_pairs_hook=unique)
 if not isinstance(p,dict):raise ValueError('Invalid CPI response object')
 if p.get('status')!='REQUEST_SUCCEEDED':raise ValueError('Unconfirmed BLS response')
 rows=p.get('Results',{}).get('series',[]);expected={v[0] for v in CONTRACT.values()}
 if len(rows)!=4 or {r.get('seriesID') for r in rows}!=expected:raise ValueError('Missing, duplicate or unexpected CPI series')
 result={}
 for key,(sid,adjustment,feature) in CONTRACT.items():
  series=next(r for r in rows if r['seriesID']==sid)
  if series.get('seasonal_adjustment',adjustment)!=adjustment:raise ValueError('CPI SA/NSA mismatch')
  if series.get('unit','index') not in ('index','Index 1982-84=100'):raise ValueError('CPI index unit mismatch')
  points={}
  for row in series.get('data',[]):
   code=row.get('period','')
   if code=='M13':continue
   if not re.fullmatch(r'M(0[1-9]|1[0-2])',code):raise ValueError('Invalid CPI month')
   year=row.get('year','')
   if not re.fullmatch(r'\d{4}',str(year)):raise ValueError('Invalid CPI year')
   ref=str(date(int(year),int(code[1:]),1))
   if int(year) not in (observed.year-1,observed.year) or ref in points:raise ValueError('Duplicate or outside requested CPI year')
   notes=row.get('footnotes',[])
   if not isinstance(notes,list) or any(not isinstance(n,dict) for n in notes):raise ValueError('Invalid CPI footnotes')
   missing=row.get('value') in ('-','.')
   confirmed=any(n.get('code')=='X' and re.search(r'data unavailable',n.get('text',''),re.I) for n in notes)
   if missing:
    if not confirmed:raise ValueError('Missing CPI index without publisher proof')
    value=None
   else:
    try:value=Decimal(row['value'])
    except (InvalidOperation,TypeError,KeyError):raise ValueError('Invalid CPI value') from None
    if not value.is_finite() or value<=0:raise ValueError('Invalid CPI level')
   points[ref]=dict(value=str(value) if value is not None else None,source_value=row['value'],footnotes=notes,missing_confirmed=missing and confirmed)
  lag=1 if feature=='mom' else 12
  required={period,month(period,-1),month(period,-lag),month(period,-lag-1)}
  if not required<=points.keys():raise ValueError('CPI dependency not yet available')
  def rate(ref):
   base=month(ref,-lag)
   if ref not in points or base not in points:return None,None
   a,b=points[ref]['value'],points[base]['value']
   if a is None or b is None:return None,None
   with localcontext() as context:
    context.prec=40;precise=(Decimal(a)/Decimal(b)-1)*100
    rounded=precise.quantize(Decimal('.1'),rounding=ROUND_HALF_UP)
   return str(rounded),str(precise)
  actual,unrounded=rate(period);previous,previous_unrounded=rate(month(period,-1));base=month(period,-lag)
  terminal=actual is None and feature=='yoy' and points[period]['value'] is not None and points[base]['missing_confirmed']
  if actual is None and not terminal:raise ValueError('CPI current index not ready')
  trend={ref:rate(ref)[0] for ref in sorted(points) if ref<=period and rate(ref)[0] is not None}
  result[key]=dict(series_id=key.split(':')[0],bls_series_id=sid,feature_name=feature,unit='percent',
   seasonal_adjustment=adjustment,reference_period=period,previous_period=month(period,-1),actual=actual,previous=previous,
   unrounded_actual=unrounded,unrounded_previous=previous_unrounded,rate_kind='derived_index_rate',method=POLICY['method'],precision=1,
   terminal=terminal,missing_base_period=base if terminal else None,missing_proof=points[base] if terminal else None,
   history=points,trend=trend,inputs={ref:points[ref] for ref in sorted(required)})
 return result


class ReportTable(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
 def handle_starttag(self,tag,attrs):
  if tag=='tr':self.row=[]
  if tag in ('td','th') and self.row is not None:self.cell=[]
 def handle_data(self,value):
  if self.cell is not None:self.cell.append(value)
 def handle_endtag(self,tag):
  if tag in ('td','th') and self.cell is not None:
   self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
  if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None


def published_report(raw,event,url):
 """Optional verified HTTP HTML, distinct from the anonymous API response."""
 day=date.fromisoformat(event['release_date']);period=date.fromisoformat(event['reference_period'])
 expected='https://www.bls.gov/news.release/archives/cpi_'+day.strftime('%m%d%Y')+'.htm'
 if url!=expected:raise ValueError('Foreign CPI report URL')
 plain=' '.join(re.sub('<[^>]+>',' ',raw.decode('utf-8')).split())
 if ('CONSUMER PRICE INDEX - '+period.strftime('%B %Y').upper()) not in plain:raise ValueError('CPI report period mismatch')
 if day.strftime('%B %d, %Y') not in plain or '8:30' not in plain:raise ValueError('CPI report release identity mismatch')
 if 'Seasonally adjusted changes from preceding month' not in plain:raise ValueError('Missing CPI SA table')
 parser=ReportTable();parser.feed(raw.decode('utf-8'));result={}
 for key,label in [('CPIAUCSL:mom','All items'),('CPILFESL:mom','All items less food and energy')]:
  rows=[r for r in parser.rows if r and r[0]==label and len(r)==9]
  if len(rows)!=1:raise ValueError('Ambiguous CPI Table A row')
  previous,actual=rows[0][-3:-1]
  if not all(re.fullmatch(r'-?\d+\.\d',v) for v in (actual,previous)):raise ValueError('Invalid published CPI rate')
  result[key]=dict(actual=actual,previous=previous)
 return result


def events(now):
 from app.analytics.release_calendar import list_calendar_events
 from app.analytics.calendar_evidence import read_evidence,period_evidence
 evidence=read_evidence();result=[]
 for e in list_calendar_events(now.date()-timedelta(days=2),now.date())['events']:
  if e.get('release_id')!=10 or not e.get('release_datetime_utc'):continue
  at=instant(e['release_datetime_utc'])
  if not at<=now<at+timedelta(seconds=POLICY['window_seconds']):continue
  proofs=[period_evidence(evidence,10,str(e['release_date']),sid) for sid in ('CPIAUCSL','CPILFESL')]
  if not all(p and p['source_url'].startswith('https://www.bls.gov/') for p in proofs):continue
  periods={p['reference_period'] for p in proofs}
  if len(periods)!=1:continue
  period=periods.pop()
  if date.fromisoformat(period)>=at.date():continue
  result.append(dict(release_id=10,release_date=str(e['release_date']),reference_period=period,scheduled_at=at.isoformat(),schedule_proofs=proofs))
 return sorted(result,key=lambda r:r['scheduled_at'],reverse=True)


def documents(c):
 result=[]
 for i,url,stamp,sha,meta in c.execute("SELECT id,source_url,retrieved_at,raw_hash,metadata FROM publisher_documents WHERE source=%s AND kind='cpi-batch' ORDER BY retrieved_at,id",(SOURCE,)):
  try:
   raw=meta['raw_utf8'].encode('utf-8')
   if url!=URL or hashlib.sha256(raw).hexdigest()!=sha or meta['contract']!=json.loads(json.dumps(POLICY)):continue
   if parse(raw,meta['event']['reference_period'])!=meta['readings'] or stamp<instant(meta['event']['scheduled_at']):continue
  except (ValueError,KeyError,TypeError):continue
  result.append(dict(id=str(i),source_url=url,retrieved_at=stamp,raw_hash=sha,metadata=meta))
 return result


def complete(c,event):
 return any(all(d['metadata']['event'].get(k)==event.get(k) for k in ('release_id','release_date','reference_period','scheduled_at')) for d in documents(c))


def fetch(client,event):
 year=date.fromisoformat(event['reference_period']).year
 request=dict(seriesid=[v[0] for v in CONTRACT.values()],startyear=str(year-1),endyear=str(year))
 with client.stream('POST',URL,json=request) as response:
  if response.status_code!=200:return None,request,response.status_code,response.headers.get('Retry-After')
  chunks=[];size=0
  for chunk in response.iter_bytes():
   size+=len(chunk)
   if size>MAX_BYTES:raise ValueError('CPI response too large')
   chunks.append(chunk)
  return b''.join(chunks),request,200,None


def store(c,raw,event,captured,request,directory):
 rows=parse(raw,event['reference_period']);sha=hashlib.sha256(raw).hexdigest();path=Path(directory)/(sha+'.json');path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('CPI raw hash collision')
 else:
  with path.open('xb') as stream:stream.write(raw)
 key=event['release_date']+':'+event['reference_period'];identifier=uuid5(NAMESPACE_URL,SOURCE+':'+key+':'+sha)
 meta=dict(version=1,event=event,readings=rows,request=request,contract=POLICY,raw_utf8=raw.decode('utf-8'),availability='current_at_capture; not proven first print')
 c.execute("""INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata)
  VALUES(%s,%s,'cpi-batch',%s,%s,200,%s,%s,%s) ON CONFLICT(source,kind,raw_hash) DO NOTHING""",(identifier,SOURCE,URL,captured,sha,str(path),Jsonb(meta)))
 return str(identifier),sha


def run(factory,token,directory,now=None,client=None,events_loader=events,crash_after_claim=False):
 from app.database.forecast_f1_authorization_cpi import authorized
 now=now or datetime.now(timezone.utc)
 with factory() as c:
  c.read_only=True;authorized(c,token);candidates=events_loader(now)
 if not candidates:return dict(status='outside_cpi_window',added=0)
 with factory() as c:
  c.autocommit=True
  if not c.execute('SELECT pg_try_advisory_lock(%s)',(budget.LOCK,)).fetchone()[0]:return dict(status='busy',added=0)
  try:
   event=candidates[0]
   if complete(c,event):return dict(status='complete',added=0)
   identifier,scope,blocked=budget.claim(c,SOURCE,event,now)
   if blocked:return dict(status=blocked,added=0)
   if crash_after_claim:raise RuntimeError('Injected CPI crash after claim')
   owned=client is None
   if owned:client=httpx.Client(timeout=25,follow_redirects=False)
   try:
    raw,request,status,retry=fetch(client,event);captured=datetime.now(timezone.utc)
    if status!=200:
     scope.update(http_status=status,phase='http_refused',retry_at=max(captured+timedelta(seconds=budget.INTERVAL),retry_after(retry,captured) if retry else captured+timedelta(hours=24)).isoformat())
     c.execute("UPDATE source_check_runs SET finished_at=%s,status='error',error_code='cpi_http_refused',scope=%s WHERE id=%s",(captured,Jsonb(scope),identifier));return dict(status='http_refused',added=0)
    with c.transaction():
     authorized(c,token);doc,sha=store(c,raw,event,captured,request,directory)
     scope.update(phase='stored',document_id=doc,raw_hash=sha,http_status=200)
     c.execute("UPDATE source_check_runs SET finished_at=%s,status='success',scope=%s WHERE id=%s",(captured,Jsonb(scope),identifier))
    return dict(status='complete',added=1,raw_hash=sha)
   except Exception:
    c.execute("UPDATE source_check_runs SET finished_at=clock_timestamp(),status='error',error_code='cpi_unconfirmed' WHERE id=%s",(identifier,));raise
   finally:
    if owned:client.close()
  finally:c.execute('SELECT pg_advisory_unlock(%s)',(budget.LOCK,))


def project(events,c,now):
 docs=documents(c)
 for e in events:
  if e.get('release_id')!=10:continue
  matching=[d for d in docs if d['retrieved_at']<=now and d['metadata']['event']['release_date']==str(e['release_date']) and instant(d['metadata']['event']['scheduled_at'])<=now]
  if not matching:continue
  doc=matching[-1]
  for m in e.get('measures',[]):
   row=doc['metadata']['readings'].get(m['series_id']+':'+m['feature_name'])
   if not row or m.get('reference_period')!=row['reference_period'] or m.get('unit')!='percent':continue
   original={k:copy.deepcopy(m.get(k)) for k in ('actual','previous','actual_provenance','previous_provenance','data_version')}
   proof=dict(source=SOURCE,source_url=URL,document_id=doc['id'],raw_hash=doc['raw_hash'],retrieved_at=doc['retrieved_at'].isoformat(),observation_period=row['reference_period'],bls_series_id=row['bls_series_id'],method=row['method'],rate_kind=row['rate_kind'],inputs=row['inputs'],unrounded=row['unrounded_actual'],first_print=False)
   m.update(actual=float(row['actual']) if row['actual'] is not None else None,previous=float(row['previous']) if row['previous'] is not None else None,
    seasonal_adjustment=row['seasonal_adjustment'],selected_source=SOURCE,data_version='derived_bls_snapshot',previous_data_version='derived_bls_snapshot',
    actual_provenance=proof,previous_provenance={**proof,'observation_period':row['previous_period'],'unrounded':row['unrounded_previous']},
    previous_period=row['previous_period'],previous_kind='previous_period',result_provenance=proof,source_url=URL,
    result_status='publisher_unavailable' if row['terminal'] else 'available',mapping_status='confirmed',comparison_status='same_cpi_capture',
    published_precision=1,previous_precision=1,cpi_rate_kind=row['rate_kind'],cpi_history=row['trend'],
    cpi_contract_id=SOURCE+':'+row['bls_series_id']+':'+row['feature_name']+':'+row['seasonal_adjustment'],
    cpi_missing_base_period=row['missing_base_period'],cpi_missing_proof=row['missing_proof'],
    missing_reason={'actual':'publisher_base_unavailable' if row['terminal'] else None,'previous':None if row['previous'] is not None else 'cpi_previous_dependency_unavailable'},fred_alternative=original)
 return events


def forecast_contract(events):
 for e in events:
  for m in e.get('measures',[]):
   if m.get('selected_source')==SOURCE and m.get('seasonal_adjustment')=='NSA':
    m.update(forecast=None,forecast_details=None,forecast_status='not_comparable_adjustment',consensus_status='not_integrated')
 return events


def store_published_report(c,raw,event,url,captured,directory):
 """Only a caller with a successful official HTTP capture may supply HTML.

 This function never turns API levels into an allegedly published percentage.
 """
 if captured<instant(event['scheduled_at']):raise ValueError('Report precedes release')
 rates=published_report(raw,event,url);sha=hashlib.sha256(raw).hexdigest()
 path=Path(directory)/(sha+'.html');path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('Report raw hash conflict')
 else:
  with path.open('xb') as stream:stream.write(raw)
 identifier=uuid5(NAMESPACE_URL,SOURCE+':report:'+event['release_date']+':'+sha)
 meta=dict(event=event,raw_utf8=raw.decode('utf-8'),rates=rates,method='published_report_rate',http_status=200)
 c.execute("INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata) VALUES(%s,%s,'cpi-report',%s,%s,200,%s,%s,%s) ON CONFLICT(source,kind,raw_hash) DO NOTHING",(identifier,SOURCE,url,captured,sha,str(path),Jsonb(meta)))
 return str(identifier)


def published_overlay(events,c,now):
 docs=c.execute("SELECT id,source_url,retrieved_at,raw_hash,metadata FROM publisher_documents WHERE source=%s AND kind='cpi-report' AND http_status=200 ORDER BY retrieved_at,id",(SOURCE,)).fetchall()
 for e in events:
  if e.get('release_id')!=10:continue
  for identifier,url,stamp,sha,meta in docs:
   try:
    event=meta['event'];raw=meta['raw_utf8'].encode('utf-8')
    if stamp>now or stamp<instant(event['scheduled_at']) or event['release_date']!=str(e['release_date']) or hashlib.sha256(raw).hexdigest()!=sha:continue
    rates=published_report(raw,event,url)
    if rates!=meta['rates']:continue
   except (ValueError,KeyError,TypeError):continue
   for m in e.get('measures',[]):
    rate=rates.get(m['series_id']+':'+m['feature_name'])
    if not rate or m.get('reference_period')!=event['reference_period'] or m.get('selected_source')!=SOURCE:continue
    m['cpi_derived_alternative']={k:copy.deepcopy(m.get(k)) for k in ('actual','previous','actual_provenance','previous_provenance')}
    proof=dict(source=SOURCE,source_url=url,document_id=str(identifier),raw_hash=sha,retrieved_at=stamp.isoformat(),observation_period=event['reference_period'],method='published_report_rate',first_print=False)
    m.update(actual=float(rate['actual']),previous=float(rate['previous']),data_version='official_release',previous_data_version='official_release',cpi_rate_kind='published_report_rate',cpi_history={},actual_provenance=proof,previous_provenance={**proof,'observation_period':m['previous_period']},source_url=url,result_provenance=proof)
 return events
