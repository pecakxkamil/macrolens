"""Forecast F1: strict identities, no retrospective knowledge, read-only projection.

Writers are isolated-only. This module never downloads or creates schema in GET.
"""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row

ROOT=Path(__file__).resolve().parents[1]
PREFIX='macrolens_forecast_f1_'
TABLES=('forecast_vintages','forecast_freezes','forecast_refresh_checks')
KINDS=('consensus','model_nowcast','issuer_guidance')
MACRO={'CPIAUCSL','CPILFESL','PCEPI','PCEPILFE','GDPC1'}

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def instant(value):
 d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('Timezone required')
 return d.astimezone(timezone.utc)

def isolated(c):
 if not c.info.dbname.startswith(PREFIX) or not 170000<=c.info.server_version<180000:
  raise ValueError('Forecast F1 writes require owned isolated PG17')

def validate(r):
 if set(r)!= {'kind','subject','value','low','high','source_id','source_url','published_at','publication_precision','methodology','source_sha256','rights','note'}:raise ValueError('Forecast contract')
 if r['kind'] not in KINDS or not r['methodology'] or not r['note']:raise ValueError('Forecast type/methodology')
 s=r['subject']
 if s.get('domain')=='macro':
  if set(s)!={'domain','country','indicator','period','transform','adjustment','unit','methodology','publication_stage'} or s['country']!='US' or s['indicator'] not in MACRO or s['unit']!='percent' or s['adjustment'] not in ('SA','NSA'):raise ValueError('Macro identity')
  if s['transform'] not in ('mom','yoy','qoq_annualized') or s['methodology']!='publisher_index_change':raise ValueError('Macro methodology')
  if s['indicator']=='GDPC1' and s['transform']!='qoq_annualized':raise ValueError('GDP SAAR')
  d=datetime.strptime(s['period'],'%Y-%m-%d')
  if d.day!=1 or s['publication_stage'] not in ('main','advance','second','third'):raise ValueError('Period/publication stage')
 elif s.get('domain')=='earnings':
  if set(s)!={'domain','company_id','cik','fiscal_year','fiscal_quarter','metric','currency','standard','eps_basis','share_basis','methodology'}:raise ValueError('Earnings identity')
  from uuid import UUID
  UUID(s['company_id'])
  if not str(s['cik']).isdigit() or not 1<=s['fiscal_quarter']<=4 or not 2000<=s['fiscal_year']<=2100 or s['metric'] not in ('revenue','reported_diluted_eps') or s['currency'] not in ('USD','EUR','TWD') or s['standard'] not in ('US_GAAP','IFRS','non_GAAP'):raise ValueError('Earnings basis')
  if s['metric']=='reported_diluted_eps' and (s['eps_basis']!='diluted' or s['share_basis'] not in ('common_share','ordinary_share','ADR')):raise ValueError('EPS basis')
  if s['metric']=='revenue' and (s['eps_basis']!='not_applicable' or s['share_basis']!='not_applicable'):raise ValueError('Revenue basis')
  if s['methodology'] not in ('consolidated_quarterly_revenue','reported_diluted_eps'):raise ValueError('Methodology')
 else:raise ValueError('Domain')
 values=[Decimal(r[k]) for k in ('low','value','high') if r[k] is not None]
 if not values or any(not n.is_finite() for n in values):raise ValueError('Finite value/range required')
 if (r['low'] is None)!=(r['high'] is None):raise ValueError('Complete range required')
 if r['low'] is not None and Decimal(r['low'])>Decimal(r['high']):raise ValueError('Range order')
 if r['value'] is not None and r['low'] is not None and not Decimal(r['low'])<=Decimal(r['value'])<=Decimal(r['high']):raise ValueError('Value outside range')
 if not r['source_url'].startswith('https://') or len(r['source_sha256'])!=64 or any(x not in '0123456789abcdef' for x in r['source_sha256']):raise ValueError('Source proof')
 instant(r['published_at'])
 if r['publication_precision'] not in ('date','instant'):raise ValueError('Publication precision')
 if r['rights'] not in ('noncommercial_attributed','public_filing_facts'):raise ValueError('Unreviewed rights')
 return r

def initialize(c):
 isolated(c)
 if any(c.execute('SELECT to_regclass(%s)',(t,)).fetchone()[0] for t in TABLES):raise ValueError('Existing/partial F1 schema; no automatic repair')
 c.execute((ROOT/'app/database/forecast_f1_schema.sql').read_text(encoding='utf-8'))

def append(c,records):
 isolated(c)
 return _append_prepared(c,records)

def _append_prepared(c,records,id_factory=None):
 # Only isolated append or the separately authorized activation/runtime calls this.
 for r in records:validate(r)
 added=0
 for r in records:
  key=digest(r['subject']);fp=digest(r)
  c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,726530030))',(key,))
  last=c.execute('SELECT version,fingerprint,payload FROM forecast_vintages WHERE subject_key=%s AND kind=%s AND source_id=%s ORDER BY version DESC LIMIT 1',(key,r['kind'],r['source_id'])).fetchone()
  if last and (last[1]==fp or {k:v for k,v in last[2].items() if k!='source_sha256'}=={k:v for k,v in r.items() if k!='source_sha256'}):continue
  if c.execute('SELECT 1 FROM forecast_vintages WHERE fingerprint=%s',(fp,)).fetchone():raise ValueError('Old forecast cannot reactivate')
  if instant(r['published_at'])>datetime.now(timezone.utc):raise ValueError('Future publication evidence')
  c.execute('INSERT INTO forecast_vintages(forecast_id,subject_key,kind,source_id,version,fingerprint,payload) VALUES(%s,%s,%s,%s,%s,%s,%s)',(id_factory(r) if id_factory else uuid4(),key,r['kind'],r['source_id'],last[0]+1 if last else 1,fp,Jsonb(r)))
  added+=1
 return added

def load(c):
 present=c.execute("SELECT to_regclass('forecast_vintages'),to_regclass('forecast_freezes'),to_regclass('forecast_refresh_checks')").fetchone()
 if not any(present):return None
 if not all(present):raise ValueError('Partial forecast store')
 with c.cursor(row_factory=dict_row) as q:
  q.execute('SELECT * FROM forecast_vintages ORDER BY captured_at,version,forecast_id');v=q.fetchall()
  q.execute('SELECT * FROM forecast_freezes');f=q.fetchall()
 return v,f

def known_at(v):
 r=v['payload'];published=instant(r['published_at'])
 # Capture time proves local availability; date precision is never treated as first print.
 return max(published,instant(v['captured_at']))

def choose(store,subject,event_id,cutoff,published,now=None):
 if store is None:return None,'not_activated'
 now=now or datetime.now(timezone.utc);vs,freezes=store;key=digest(subject)
 frozen=[f for f in freezes if f['event_id']==event_id and f['subject_key']==key]
 if frozen:
  ids=[f['forecast_id'] for f in frozen if f['forecast_id']]
  eligible=[v for v in vs if v['forecast_id'] in ids]
  state='frozen'
 elif published:return None,'freeze_pending'
 else:
  if cutoff is None or now>=cutoff:return None,'release_cutoff_unconfirmed_or_passed'
  eligible=[v for v in vs if v['subject_key']==key and known_at(v)<=now and known_at(v)<cutoff]
  state='live'
 if not eligible:return None,'no_pre_release_evidence' if frozen else 'unavailable'
 # Pick newest vintage per type/provider first. A newer range-only forecast must
 # never fall back to an old point; ranges are displayed as ranges.
 latest={}
 for v in eligible:
  pair=(v['kind'],v['source_id'])
  if pair not in latest or v['version']>latest[pair]['version']:latest[pair]=v
 selected=sorted(latest.values(),key=lambda v:(KINDS.index(v['kind']),-known_at(v).timestamp()))[0]
 r=selected['payload'];return dict(r,forecast_id=str(selected['forecast_id']),version=selected['version'],captured_at=str(selected['captured_at']),state=state,comparison_allowed=state=='frozen'),state

def freeze(c,event_id,subject,cutoff):
 isolated(c)
 return _freeze_prepared(c,event_id,subject,cutoff)

def _freeze_prepared(c,event_id,subject,cutoff):
 key=digest(subject)
 c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,726530030))',(event_id+key,))
 if c.execute('SELECT 1 FROM forecast_freezes WHERE event_id=%s AND subject_key=%s',(event_id,key)).fetchone():return False
 store=load(c)
 if cutoff>datetime.now(timezone.utc):raise ValueError('Cannot freeze future publication')
 vs=store[0];eligible=[v for v in vs if v['subject_key']==key and known_at(v)<cutoff]
 for kind in KINDS:
  matches=[v for v in eligible if v['kind']==kind];v=max(matches,key=known_at) if matches else None
  c.execute('INSERT INTO forecast_freezes(event_id,subject_key,kind,release_cutoff,forecast_id,reason) VALUES(%s,%s,%s,%s,%s,%s)',(event_id,key,kind,cutoff,v['forecast_id'] if v else None,'last_pre_release' if v else 'no_pre_release_evidence'))
 return True

def macro_subject(m,event=None):
 if m.get('series_id') not in MACRO or m.get('mapping_status')!='confirmed' or not m.get('reference_period'):return None
 return dict(domain='macro',country='US',indicator=m['series_id'],period=m['reference_period'],transform=m['feature_name'],adjustment='SA',unit=m['unit'],methodology='publisher_index_change',publication_stage=(event or {}).get('estimate_stage') or 'main')

def earnings_subject(e,metric,previous=False):
 period=e.get('previous_period') if previous else e
 if not period:return None
 actual=e.get(('previous_' if previous else 'current_')+('eps_actual' if metric=='reported_diluted_eps' else 'revenue_actual'))
 # Future basis is taken only from reviewed issuer registry, never country.
 registry=json.loads((ROOT/'config/forecast_f1_reviewed.json').read_text(encoding='utf-8'))['earnings_basis']
 basis=registry.get(e['ticker'])
 if not basis:return None
 currency=actual['currency'] if actual else basis['currency'];standard=actual.get('reporting_standard') if actual else basis['standard']
 return dict(domain='earnings',company_id=e['company_id'],cik=str(e['cik']),fiscal_year=period['fiscal_year'],fiscal_quarter=period['fiscal_quarter'],metric=metric,currency=currency,standard=standard,eps_basis='diluted' if metric=='reported_diluted_eps' else 'not_applicable',share_basis=(actual.get('share_basis') if actual else basis['share_basis']) if metric=='reported_diluted_eps' else 'not_applicable',methodology='reported_diluted_eps' if metric=='reported_diluted_eps' else 'consolidated_quarterly_revenue')

def earnings_cutoff(e):
 release=e.get('release',{})
 if release.get('precision')=='exact' and release.get('scheduled_at_utc'):return instant(release['scheduled_at_utc'])
 # Date-only actual cannot justify knowing a forecast later on that day.
 day=e.get('financial_release_date') or release.get('source_local_date')
 if not day:return None
 from zoneinfo import ZoneInfo
 return datetime.fromisoformat(str(day)).replace(tzinfo=ZoneInfo(release.get('source_timezone') or 'America/New_York')).astimezone(timezone.utc)

def enrich_macro(events,c):
 store=load(c)
 for e in events:
  for m in e.get('measures',[]):
   s=macro_subject(m,e)
   if not s:continue
   cutoff=instant(e['release_datetime_utc']) if e.get('release_datetime_utc') else None
   r,status=choose(store,s,e['event_id'],cutoff,m.get('actual') is not None)
   m.update(forecast_details=r,forecast_status=status)
   if r:
    m['forecast']=float(r['value']) if r['value'] is not None else None
    m['consensus_status']='available' if r['kind']=='consensus' else 'not_integrated'
 return events

def enrich_earnings(events,c):
 store=load(c)
 if store is None:
  return events
 periods={(str(company),fy,q):'earnings:'+str(event) for event,company,fy,q in c.execute('SELECT e.event_id,e.company_id,p.fiscal_year,p.fiscal_quarter FROM earnings_events e JOIN earnings_periods p USING(period_id)').fetchall()}
 for e in events:
  for previous in (False,True):
   for metric,short in [('reported_diluted_eps','eps'),('revenue','revenue')]:
    s=earnings_subject(e,metric,previous)
    if s is None:continue
    # Previous must use the previous event's own freeze, not today's cutoff.
    event_id=e['event_id'] if not previous else 'unbound_previous'
    if previous:
     event_id=periods.get((e['company_id'],s['fiscal_year'],s['fiscal_quarter']),'unbound_previous')
    r,status=choose(store,s,event_id,earnings_cutoff(e) if not previous else None,previous or e.get('publication_state',{}).get('code','').startswith('published'))
    e[('previous_' if previous else 'current_')+short+'_forecast']=dict(r,actual=r['value'],metric=metric,currency=s['currency'],unit='currency' if metric=='revenue' else 'currency/share') if r else None
    e[('previous_' if previous else 'current_')+short+'_forecast_status']=status
 return events


def project_earnings(events,factory=None):
 from app.database.connection import get_independent_connection
 with (factory or get_independent_connection)() as c:
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  return enrich_earnings(events,c)
