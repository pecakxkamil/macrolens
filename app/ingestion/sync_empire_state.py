"""Direct NY Fed monthly GACDISA through the existing refresh transaction.

No FRED, inferred dates, PDF URL construction, or numerical PDF fallback.
Daily observations use the existing store; immutable RAW/receipts keep intraday
revisions without changing any existing observation uniqueness constraint.
"""
import calendar
import copy
import csv
import hashlib
import io
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

from pypdf import PdfReader
from app.ingestion.sync_fomc_calendar import Tree
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check

ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT/'data/raw/nyfed_empire_state'
SOURCE = 'nyfed_empire_state'
SID = 'NYFED_EMPIRE_GACDISA'
HOME = 'https://www.newyorkfed.org/survey/empire/empiresurvey_overview'
CSV = 'https://www.newyorkfed.org/medialibrary/media/survey/empire/data/esms_seasonallyadjusted_diffusion.csv'
TERMS = 'https://www.newyorkfed.org/privacy/termsofuse'
DEFINITIONS = 'https://www.newyorkfed.org/medialibrary/media/survey/empire/data/all_data_idx.pdf'
TIME_SOURCE = 'https://www.newyorkfed.org/research/calendars/nationalecon_cal'
NAME = 'Empire State Manufacturing Survey'
LABEL = 'General Business Conditions — SA'
ATTRIBUTION = '© {year} Federal Reserve Bank of New York. Content from the New York Fed subject to the Terms of Use at newyorkfed.org.'
USAGE = 'MacroLens normalizes observation dates and computes index-point differences. These modifications are not by the New York Fed. The New York Fed does not endorse MacroLens. Redistributed NY Fed content remains subject to the same Terms of Use; no additional restrictions on that content are imposed.'


def identity(period):
    return 'empire-state:'+period[:7]+':monthly'


def previous_month(period):
    d=date.fromisoformat(period);n=d.year*12+d.month-2
    return str(date(n//12,n%12+1,1))


def parse_csv(content):
    text=content.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text),strict=True)
    fields=reader.fieldnames or []
    if len(fields)!=len(set(fields)) or not {'surveyDate','GACDISA'}<=set(fields):
        raise ValueError('Missing or duplicate Current SA column')
    values={}
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError('Truncated CSV row')
        raw_date=row['surveyDate'].strip()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw_date):raise ValueError('Invalid surveyDate')
        day=date.fromisoformat(raw_date);period=str(day.replace(day=1))
        text=row['GACDISA'].strip()
        if text.upper() in ('','ND','NAN','INF','+INF','-INF','INFINITY','-INFINITY','+INFINITY'):
            value=None
        else:
            if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',text):raise ValueError('Invalid GACDISA')
            value=float(text)
            if not math.isfinite(value):value=None
            elif not -100<=value<=100:raise ValueError('Diffusion index outside range')
        if period in values:raise ValueError('Duplicate survey month')
        values[period]=value
    if not values or not any(v is not None for v in values.values()):raise ValueError('Empty CSV')
    return dict(sorted(values.items()))


def official_report_url(url):
    p=urlparse(url)
    return p.scheme=='https' and p.hostname=='www.newyorkfed.org' and not(p.username or p.password) and p.path.startswith('/medialibrary/media/survey/empire/') and p.path.endswith('.pdf')


def parse_schedule(html,proof):
    root=Tree(html).root;text=' '.join(root.text().split())
    if 'Empire State Manufacturing Survey' not in text or not re.search(r'8:30\s*a\.m\.',text):
        raise ValueError('Survey/clock not confirmed')
    # Require a printed year adjoining the calendar, not a year in a URL.
    blocks=re.findall(r'<(?:strong|h[1-6])\b[^>]*>\s*(?:<br\s*/?>\s*)?(20\d{2})\s*</(?:strong|h[1-6])>\s*</div>\s*(<table\b.*?</table>)',html,re.S|re.I)
    if not blocks:raise ValueError('No explicit annual survey calendar')
    rows={}
    for year,markup in blocks:
        table=Tree(markup).root.find(lambda n:n.tag=='table')[0]
        tr=table.find(lambda n:n.tag=='tr')
        if len(tr)!=6:raise ValueError('Incomplete annual survey calendar')
        for offset in range(0,6,2):
            months=tr[offset].find(lambda n:n.tag in ('td','th'))
            days=tr[offset+1].find(lambda n:n.tag in ('td','th'))
            if len(months)!=4 or len(days)!=4:raise ValueError('Invalid calendar columns')
            for i,(m,cell) in enumerate(zip(months,days)):
                month=offset*2+i+1
                if m.text().strip().upper()!=calendar.month_abbr[month].upper():raise ValueError('Calendar month mismatch')
                day=re.fullmatch(r'(\d{1,2})(?:\s+report)?',' '.join(cell.text().split()),re.I)
                if not day:raise ValueError('Ambiguous calendar date')
                period=str(date(int(year),month,1));release=str(date(int(year),month,int(day[1])))
                links={urljoin(HOME,a.attrs.get('href','')) for a in cell.find(lambda n:n.tag=='a')}
                if len(links)>1 or any(not official_report_url(u) for u in links):raise ValueError('Ambiguous report link')
                item=dict(event_id=identity(period),reference_period=period,release_date=release,
                    release_time='08:30:00',source_timezone='America/New_York',date_status='confirmed',time_status='confirmed',
                    source_url=HOME,time_source_url=TIME_SOURCE,document_url=next(iter(links),None),
                    schedule_status='confirmed',schedule_provenance=copy.deepcopy(proof))
                if period in rows and rows[period]!=item:raise ValueError('Conflicting calendar years')
                rows[period]=item
    return sorted(rows.values(),key=lambda r:r['reference_period'])


def parse_report_text(pages,period):
    d=date.fromisoformat(period)
    if not pages or 'Empire State' not in pages[0] or 'Manufacturing Survey' not in ' '.join(pages[0].split()):raise ValueError('Wrong PDF survey')
    if not re.search(calendar.month_name[d.month]+r'\s+'+str(d.year),pages[0]):raise ValueError('Wrong PDF month/year')
    # First Current chart only. Future charts elsewhere must never supply Actual.
    if len(pages)<2:raise ValueError('Missing Current PDF table')
    text=' '.join(pages[1].split())
    if 'Current Indicators Change from Preceding Month' not in text or 'Seasonally Adjusted' not in ' '.join(pages[0].split()):
        raise ValueError('Current seasonally adjusted PDF section not confirmed')
    pattern=r'(?<!Future )General Business Conditions Percent Reporting Higher Lower Index\s+([A-Za-z]{3})\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+([A-Za-z]{3})\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+Change'
    matches=re.findall(pattern,text)
    if len(matches)!=1:raise ValueError('Ambiguous Current PDF table')
    a,_,_,previous,b,_,_,current=matches[0]
    prior=date.fromisoformat(previous_month(period))
    if a!=calendar.month_abbr[prior.month] or b!=calendar.month_abbr[d.month]:raise ValueError('Wrong PDF table months')
    current=float(current);previous=float(previous)
    if any(not math.isfinite(x) or not -100<=x<=100 for x in (current,previous)):raise ValueError('Invalid PDF index')
    return dict(reference_period=period,current=current,previous=previous,publication_time=None,
                validation='explicit_month_year_and_current_sa_table')


def parse_report(content,period):
    reader=PdfReader(io.BytesIO(content))
    return parse_report_text([p.extract_text() or '' for p in reader.pages],period)


def merge_schedule(old,incoming,stamp):
    events={r['event_id']:copy.deepcopy(r) for r in old.get('events',[])};history=copy.deepcopy(old.get('history',[]))
    for candidate in incoming:
        key=candidate['event_id'];prior=events.get(key)
        if prior and prior['release_date']==candidate['release_date'] and not candidate.get('document_url'):
            candidate={**candidate,'document_url':prior.get('document_url')}
        if prior and any(prior.get(k)!=candidate.get(k) for k in ('release_date','release_time','document_url')):
            history.append(dict(event_id=key,replaced_at=stamp,previous=prior))
            candidate={**candidate,'schedule_status':'changed'}
        elif prior:candidate={**candidate,'schedule_status':prior.get('schedule_status','confirmed')}
        events[key]=candidate
    return dict(events=sorted(events.values(),key=lambda r:r['reference_period']),history=history)


def receipts(connection):
    with connection.cursor() as cur:
        cur.execute('SELECT id,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata FROM publisher_documents WHERE source=%s ORDER BY retrieved_at,id',(SOURCE,))
        return [dict(zip(('id','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata'),r)) for r in cur.fetchall()]


def read_schedule(connection=None):
    from app.database.connection import get_connection
    owned=connection is None;connection=connection or get_connection()
    try:
        docs=[r for r in receipts(connection) if r['kind']=='schedule']
        return docs[-1]['metadata'] if docs else dict(events=[],history=[])
    finally:
        if owned:connection.close()


def capture(response,url,now,raw_root=None):
    root=Path(raw_root or RAW_ROOT);root.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(response.content).hexdigest();path=root/(digest+'.raw')
    if not path.exists():
        temp=root/(uuid4().hex+'.tmp');temp.write_bytes(response.content);temp.replace(path)
    elif hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Corrupt retained RAW')
    return dict(id=str(uuid4()),source=SOURCE,source_url=url,retrieved_at=now.isoformat(),http_status=response.status_code,
                raw_hash=digest,raw_path=str(path.resolve().relative_to(ROOT)) if ROOT in path.resolve().parents else str(path.resolve()))


def store_receipt(connection,kind,proof,metadata):
    with connection.cursor() as cur:
        cur.execute('''INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(source,kind,raw_hash) DO NOTHING RETURNING id''',
            (proof['id'],SOURCE,kind,proof['source_url'],proof['retrieved_at'],proof['http_status'],proof['raw_hash'],proof['raw_path'],json.dumps(metadata)))
        result=cur.fetchone()
        if result:return str(result[0])
        cur.execute('SELECT id FROM publisher_documents WHERE source=%s AND kind=%s AND raw_hash=%s',(SOURCE,kind,proof['raw_hash']))
        return str(cur.fetchone()[0])


def load_observations(connection):
    with connection.cursor() as cur:
        cur.execute('''SELECT DISTINCT ON(observation_date) observation_date,value,vintage_date,source_document_id,publication_document_id
            FROM observation_vintages WHERE series_id=%s AND source=%s ORDER BY observation_date,vintage_date DESC,id DESC''',(SID,SOURCE))
        return {str(day):dict(value=float(v) if v is not None else None,vintage_date=str(vintage),document_id=str(doc),publication_document_id=str(pub) if pub else None) for day,v,vintage,doc,pub in cur.fetchall()}


def admitted(period,value,event,report,old,now):
    if value is None:return 'observation_missing'
    instant=datetime.fromisoformat(event['release_date']+'T'+event['release_time']).replace(tzinfo=ZoneInfo('America/New_York'))
    if now<instant:return 'not_yet_published'
    if not report:return 'empire_report_not_confirmed'
    if report['reference_period']!=period:return 'empire_report_not_confirmed'
    # An already verified period may be revised by the current historical CSV.
    if report['current']!=value and not (old and old.get('publication_document_id')):return 'empire_source_conflict'
    return None


def sync_source(client,connection,now=None,raw_root=None,history_periods=(),clock=None):
    now=now or datetime.now(timezone.utc);stamp=now.isoformat();errors=[];captures=[]
    # Initial window: current month and two predecessors; future jobs preserve it.
    n=now.year*12+now.month-3;initial=str(date(n//12,n%12+1,1))
    def fetch(url):
        before_request('NY Fed');response=client.get(url)
        parsed=urlparse(str(response.url))
        if parsed.scheme!='https' or parsed.hostname!='www.newyorkfed.org' or parsed.username or parsed.password:raise ValueError('Unexpected NY Fed redirect')
        fetched=clock() if clock else datetime.now(timezone.utc)
        proof=capture(response,url,fetched,raw_root);captures.append(proof);response.raise_for_status()
        return response.content,proof
    with connection.transaction(), availability_check('nyfed:empire-state',{'provider':'Federal Reserve Bank of New York','series_ids':[SID]},connection=connection) as check:
        # Database savepoint includes observations and schedule/document receipts.
        with connection.transaction():
            docs=receipts(connection);old_schedule=read_schedule(connection);old_obs=load_observations(connection)
            start=old_schedule.get('retained_from',initial)
            try:
                content,proof=fetch(HOME)
                known_schedules=[d for d in docs if d['kind']=='schedule']
                if known_schedules and proof['raw_hash']!=known_schedules[-1]['raw_hash'] and any(d['raw_hash']==proof['raw_hash'] for d in known_schedules):raise ValueError('Older calendar replayed')
                parsed=parse_schedule(content.decode('utf-8'),proof)
                schedule=merge_schedule(old_schedule,parsed,stamp);schedule['retained_from']=start
                store_receipt(connection,'schedule',proof,schedule)
                schedule_ok=True
            except Exception as e:
                schedule=old_schedule;schedule_ok=False;errors.append(dict(stage='schedule',error=type(e).__name__))
            report_docs={d['metadata']['reference_period']:d for d in docs if d['kind']=='report'}
            candidates=[e for e in schedule['events'] if e['release_date']<=str(now.date()) and e['reference_period']>=start and e.get('document_url')]
            # Normal job fetches only the latest due report. Explicit audit may
            # validate two historical reports without enabling a history crawler.
            wanted=set(history_periods)
            if candidates:wanted.add(max(candidates,key=lambda e:e['reference_period'])['reference_period'])
            latest=max((e['reference_period'] for e in candidates),default=None)
            for event in candidates:
                period=event['reference_period']
                if period not in wanted or (period!=latest and period in report_docs and report_docs[period]['source_url']==event['document_url']):continue
                try:
                    content,proof=fetch(event['document_url']);metadata=parse_report(content,period)
                    known_reports=[d for d in docs if d['kind']=='report' and d['metadata']['reference_period']==period]
                    if known_reports and proof['raw_hash']!=known_reports[-1]['raw_hash'] and any(d['raw_hash']==proof['raw_hash'] for d in known_reports):raise ValueError('Older PDF replayed')
                    docid=store_receipt(connection,'report',proof,metadata)
                    report_docs[period]={**proof,'id':docid,'metadata':metadata}
                except Exception as e:errors.append(dict(stage='report',period=period,error=type(e).__name__))
            reasons={};revisions=[];changed=0;csv_ok=False;bindings={}
            try:
                content,proof=fetch(CSV);values=parse_csv(content)
                known_csv=[d for d in docs if d['kind']=='csv']
                if known_csv and proof['raw_hash']!=known_csv[-1]['raw_hash'] and any(d['raw_hash']==proof['raw_hash'] for d in known_csv):
                    raise ValueError('Older CSV version replayed')
                if old_obs and max(values)<max(old_obs):raise ValueError('Older or truncated CSV')
                required=[p for p in old_obs if p>=start]
                if any(p not in values for p in required):raise ValueError('Previously retained month missing')
                events={e['reference_period']:e for e in schedule['events']}
                accepted={};bindings={}
                for period,value in values.items():
                    if period<start or period not in events:continue
                    doc=report_docs.get(period)
                    reason=admitted(period,value,events[period],doc['metadata'] if doc else None,old_obs.get(period),now)
                    if reason=='empire_report_not_confirmed' and value is not None and any(
                        previous_month(p)==period and d['metadata']['previous']==value
                        for p,d in report_docs.items()):
                        # Context from the next verified report may support
                        # Previous, but cannot confirm this month's own Actual.
                        reason=None
                    if reason:reasons[period]=reason
                    else:
                        accepted[period]=value
                        bindings[period]=str(doc['id']) if doc else None
                for p,v in accepted.items():
                    if p in old_obs and v!=old_obs[p]['value']:revisions.append(dict(period=p,before=old_obs[p]['value'],after=v,previous_document_id=old_obs[p]['document_id']))
                docid=store_receipt(connection,'csv',proof,dict(column='GACDISA',retained_from=start,accepted_periods=sorted(accepted),latest_csv_period=max(values),revisions=revisions,missing_results=reasons))
                with connection.cursor() as cur:
                    cur.execute('''INSERT INTO series(series_id,name,short_name,category,frequency,unit) VALUES (%s,%s,%s,'growth','monthly','index points') ON CONFLICT(series_id) DO NOTHING''',(SID,NAME,LABEL))
                    for period,value in accepted.items():
                        if old_obs.get(period,{}).get('value')==value and old_obs[period].get('publication_document_id')==bindings[period]:continue
                        cur.execute('''INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source,source_document_id,publication_document_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(series_id,observation_date,vintage_date)
                            DO UPDATE SET value=EXCLUDED.value,source_document_id=EXCLUDED.source_document_id,
                                publication_document_id=EXCLUDED.publication_document_id,ingested_at=CURRENT_TIMESTAMP
                            WHERE observation_vintages.source=%s AND (observation_vintages.value IS DISTINCT FROM EXCLUDED.value
                                OR observation_vintages.publication_document_id IS DISTINCT FROM EXCLUDED.publication_document_id)''',
                            (SID,period,now.date(),value,SOURCE,docid,bindings[period],SOURCE));changed+=1
                csv_ok=True
            except Exception as e:
                # SQL failures must roll back, never turn an aborted transaction
                # into a successful snapshot. Network/format errors preserve data.
                import psycopg
                if isinstance(e,psycopg.Error):raise
                errors.append(dict(stage='csv',error=type(e).__name__))
            due=[e['reference_period'] for e in schedule['events'] if datetime.fromisoformat(e['release_date']+'T'+e['release_time']).replace(tzinfo=ZoneInfo('America/New_York'))<=now]
            latest_due=max(due,default=None)
            pending=bool(latest_due and latest_due>=start and not(bindings.get(latest_due) or old_obs.get(latest_due,{}).get('publication_document_id')))
            pending=pending or latest_due in reasons
            scope=dict(schedule_checked=schedule_ok,csv_validated=csv_ok,captures=captures,changed_observations=changed,
                historical_revisions=revisions,missing_results=reasons,errors=errors,
                confirmed_years=sorted({int(e['reference_period'][:4]) for e in schedule['events']}),
                latest_report_period=max(report_docs,default=None),latest_due_period=latest_due,result_pending=pending,retained_from=start)
            # Store the validated check in the SAME transaction as observations.
            # Existing availability_check also records the attempt independently.
            check['scope'].update(scope)
            check.update(status='error' if errors and not(schedule_ok or csv_ok) else 'partial' if errors or pending or any(v=='empire_source_conflict' for v in reasons.values()) else 'success',
                         error_code='empire_source_incomplete' if errors else None)
        return dict(status=check['status'],**scope)
