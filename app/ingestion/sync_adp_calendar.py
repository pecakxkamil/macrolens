"""Monthly ADP schedule/document metadata only; never import payroll results."""
import calendar
import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.ingestion.sync_fomc_calendar import Tree
from app.ingestion.sync_michigan_calendar import write_snapshot
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check

ROOT = Path(__file__).resolve().parents[2]
REVIEWED = ROOT/'config/adp_calendar_evidence.json'
SNAPSHOT = ROOT/'data/derived/adp_calendar_v1.json'
HOME = 'https://adpemploymentreport.com/'
LISTING = 'https://mediacenter.adp.com/press-releases?l=100'
AGREEMENT = 'https://www.adp.com/legal.aspx'
ADAPTER_VERSION = 1
MONTHS = {name.lower():i for i,name in enumerate(calendar.month_name) if name}
MONTH_NAMES = '|'.join(calendar.month_name[1:])


def identity(period):
    return 'adp:'+period[:7]+':monthly'


def read_schedule(path=None):
    rows,history,check = {},[],None
    history_seen=set()
    for source in ([Path(path)] if path else [REVIEWED,SNAPSHOT]):
        try:
            data=json.loads(source.read_text(encoding='utf-8'))
            if data['version']!=1:continue
            valid={}
            for row in data['events']:
                if row['report_kind']!='monthly' or not row['event_id'].startswith('adp:'):
                    raise ValueError('Invalid ADP identity')
                date.fromisoformat(row['release_date'])
                if row.get('reference_period'):date.fromisoformat(row['reference_period'])
                valid[row['event_id']]=row
            rows.update(valid)
            for entry in data.get('history',[]):
                signature=json.dumps(entry,sort_keys=True)
                if signature not in history_seen:history.append(entry);history_seen.add(signature)
            check=data.get('check') or check
        except (OSError,ValueError,KeyError,TypeError):continue
    return dict(version=1,events=sorted(rows.values(),key=lambda r:r['event_id']),history=history,check=check)


def monthly_url(url):
    p=urlparse(url)
    return p.scheme=='https' and p.hostname=='mediacenter.adp.com' and bool(re.match(r'/20\d\d-\d\d-\d\d-ADP-National-Employment-Report-',p.path)) and not re.search('preliminary|pulse',p.path,re.I)


def discover_monthly(html,now):
    """Only explicit monthly release links, not weekly Preliminary Estimates."""
    links={}
    for anchor in Tree(html).root.find(lambda n:n.tag=='a'):
        label=' '.join(anchor.text().split());url=anchor.attrs.get('href','')
        if 'ADP National Employment Report:' not in label or re.search('Preliminary|Pulse',label,re.I) or not monthly_url(url):continue
        published=urlparse(url).path[1:11]
        if published<=str(now.date()):links[url]=published
    return sorted(links,key=lambda url:(links[url],url),reverse=True)


def row(period,day,proof,clock=None,document=None):
    return dict(event_id=identity(period),report_kind='monthly',reference_period=period,
        release_date=day,release_time=clock,date_status='confirmed',reference_period_status='confirmed',
        source_timezone='America/New_York',time_status='confirmed' if clock else 'unconfirmed',
        schedule_status='confirmed',schedule_provenance=copy.deepcopy(proof),
        time_source_url=proof['source_url'] if clock else None,time_provenance=copy.deepcopy(proof) if clock else None,
        document_url=document,document_status='available' if document else 'unconfirmed',
        document_provenance=copy.deepcopy(proof) if document else None)


def parse_release(html,url,proof,now):
    if not monthly_url(url):raise ValueError('Not a monthly ADP release URL')
    tree=Tree(html).root
    title=' '.join(' '.join(n.text().split()) for n in tree.find(lambda n:n.tag in ('title','h1')))
    text=' '.join(tree.text().split())
    if 'ADP National Employment Report:' not in title or re.search('Preliminary Estimate|NER Pulse',title,re.I):
        raise ValueError('Not a monthly ADP document')
    matches=set(re.findall(rf'\b({MONTH_NAMES})\s+(20\d{{2}})\s+Report Highlights\b',text))
    if len(matches)!=1:raise ValueError('ADP report month is not explicit')
    month,year=matches.pop();period=str(date(int(year),MONTHS[month.lower()],1))
    published=urlparse(url).path[1:11];day=date.fromisoformat(published)
    # Require the document's own publication date, not merely a date in its URL.
    names={calendar.month_name[day.month],calendar.month_abbr[day.month]}
    if day.month==9:names.add('Sept')
    date_pattern='(?:'+'|'.join(names)+r')\.?\s+'+str(day.day)+r',?\s+'+str(day.year)
    if day>now.date() or not re.search(date_pattern,text):raise ValueError('ADP publication date unconfirmed')
    result=[row(period,published,proof,document=url)]
    pattern=rf'The ({MONTH_NAMES}) (20\d{{2}}) ADP National Employment Report\s+will be released on ({MONTH_NAMES}) (\d{{1,2}}), (20\d{{2}})(?: at (\d{{1,2}}):(\d{{2}}) ([ap])\.m\. ET)?\.'
    announcements=set(re.findall(pattern,text))
    if len(announcements)>1:raise ValueError('Conflicting ADP announcements')
    for ref,y,m,d,release_year,h,minute,half in announcements:
        ref_period=str(date(int(y),MONTHS[ref.lower()],1))
        release_day=str(date(int(release_year),MONTHS[m.lower()],int(d)))
        clock=None
        if h:
            if not 1<=int(h)<=12 or not 0<=int(minute)<60:raise ValueError('Invalid ADP clock')
            clock=f'{int(h)%12+(12 if half=="p" else 0):02}:{int(minute):02}:00'
        result.append(row(ref_period,release_day,proof,clock))
    return result


def merge_rows(existing, incoming, stamp, history):
    semantic=('reference_period','release_date','release_time','document_url','document_status')
    for candidate in incoming:
        key=candidate['event_id'];old=existing.get(key)
        if old is None:
            same_period=[r for r in existing.values() if candidate.get('reference_period') and r.get('reference_period')==candidate['reference_period']]
            if len(same_period)>1:raise ValueError('Conflicting ADP monthly identities')
            if same_period:old=same_period[0];key=old['event_id']
        if old is None:
            # A reviewed date-only calendar record may later acquire a month.
            same=[r for r in existing.values() if r['release_date']==candidate['release_date'] and not r.get('reference_period')]
            if len(same)==1:old=same[0];key=old['event_id']
        current=copy.deepcopy(candidate);current['event_id']=key
        if old:
            old_stamp=old['schedule_provenance'].get('document_date','')
            new_stamp=current['schedule_provenance'].get('document_date','')
            if old_stamp and new_stamp and new_stamp<old_stamp:continue
            current['schedule_status']=old.get('schedule_status','confirmed')
            for name in ('release_time','time_source_url','time_provenance','document_url','document_provenance'):
                if not current.get(name) and old.get(name):current[name]=old[name]
            if current.get('release_time'):current['time_status']='confirmed'
            if current.get('document_url'):current['document_status']='available'
            if old['release_date']!=current['release_date'] and not candidate.get('release_time'):
                current.update(release_time=None,time_status='unconfirmed',time_source_url=None,time_provenance=None)
            if old['release_date']!=current['release_date'] and not candidate.get('document_url'):
                current.update(document_url=None,document_status='unconfirmed',document_provenance=None)
            if any(old.get(k)!=current.get(k) for k in semantic):
                history.append(dict(event_id=key,replaced_at=stamp,previous=copy.deepcopy(old)))
                if old['release_date']!=current['release_date'] or (old.get('release_time') and current.get('release_time') and old['release_time']!=current['release_time']):current['schedule_status']='changed'
        existing[key]=current


def sync_schedule(client,now=None,path=None):
    """Bounded public metadata checks. A JS shell is not schedule confirmation."""
    now=now or datetime.now(timezone.utc);stamp=now.isoformat();prior=read_schedule(path)
    rows={r['event_id']:copy.deepcopy(r) for r in prior['events']};history=prior['history'][:]
    captures,errors=[],[];discovered=[]
    def fetch(url):
        before_request('ADP');response=client.get(url)
        if urlparse(str(response.url)).hostname not in ('adpemploymentreport.com','www.adpemploymentreport.com','mediacenter.adp.com'):raise ValueError('Unexpected ADP redirect')
        proof=dict(source_url=url,retrieved_at=stamp,http_status=response.status_code,
            raw_hash=hashlib.sha256(response.content).hexdigest(),response_body_retained=False,retrieval_method='backend_http_metadata_only')
        captures.append(proof);response.raise_for_status();return response,proof
    with availability_check('adp:calendar',{'provider':'ADP','scope':'monthly schedule/document metadata only; no payroll results'}) as check:
        try:
            response,proof=fetch(HOME)
            # The current publisher calendar is JavaScript-rendered. No hidden
            # endpoint, browser service or guessed monthly rule is substituted.
            raise ValueError('publisher_calendar_requires_review')
        except Exception as e:errors.append({'source_url':HOME,'error_code':str(e) if isinstance(e,ValueError) else type(e).__name__})
        active_url=LISTING
        try:
            response,_=fetch(LISTING);discovered=discover_monthly(response.text,now)
            if not discovered:raise ValueError('monthly_release_not_discovered')
            # Only the newest monthly release; never crawl numeric report history.
            url=discovered[0];active_url=url;response,proof=fetch(url)
            proof['document_date']=urlparse(url).path[1:11]
            merge_rows(rows,parse_release(response.text,url,proof,now),stamp,history)
        except Exception as e:errors.append({'source_url':active_url,'error_code':type(e).__name__})
        scope=dict(dates=sorted(r['release_date'] for r in rows.values()),
            confirmed_periods=sorted(r['reference_period'] for r in rows.values() if r.get('reference_period')),
            calendar_automation='bounded_announcements_only',latest_monthly_document=discovered[0] if discovered else None,
            errors=errors,captures=captures,results_integration='publisher_permission_required')
        check['scope'].update(scope)
        check.update(status='partial' if rows else 'error',error_code='adp_full_schedule_not_automated')
        payload=dict(version=1,adapter_version=ADAPTER_VERSION,events=sorted(rows.values(),key=lambda r:r['event_id']),history=history,
            check=dict(status=check['status'],checked_at=stamp,**scope))
        write_snapshot(payload,Path(path or SNAPSHOT))
    return payload
