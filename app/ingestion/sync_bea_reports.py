"""Bounded BEA published rates for existing GDP/PIO events, never FRED ingestion."""
import calendar
import json
import re
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
import httpx
from pathlib import Path
from urllib.parse import urljoin, urlparse

import psycopg
from app.ingestion.sync_fomc_calendar import Tree
from app.ingestion.sync_calendar_periods import parse_bea_result, parse_bea_clock, parse_schedule, parsed_date, cells
from app.ingestion.sync_empire_state import capture
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check,record_progress

SOURCE='bea_official'
RESOURCE='bea:reports'
SCHEDULE='https://www.bea.gov/news/schedule/full'
TERMS='https://www.bea.gov/help/faq/147'
ATTRIBUTION='Source: U.S. Bureau of Economic Analysis'
RAW_ROOT=Path(__file__).resolve().parents[2]/'data/raw/bea_official'
MODIFICATIONS='MacroLens normalizes periods and compares published rounded rates; no BEA endorsement is implied.'
MEASURES={('GDPC1','qoq_annualized'):'Real GDP, quarterly percent change SAAR',
 ('PCEPI','mom'):'PCE price index, monthly percent change SA',
 ('PCEPILFE','mom'):'PCE price index excluding food and energy, monthly percent change SA',
 ('PCEPILFE','yoy'):'PCE price index excluding food and energy, percent change from year ago',
 ('PCEC96','mom'):'Real PCE, monthly percent change SA',
 ('DSPIC96','mom'):'Real disposable personal income, monthly percent change SA',
 ('PSAVERT','raw'):'Personal saving as a percentage of disposable personal income, SA level'}


def official(url):
    p=urlparse(url)
    return p.scheme=='https' and p.hostname in ('bea.gov','www.bea.gov') and p.path.startswith('/news/')


def key(proof):
    return f"{proof['release_id']}:{proof['reference_period']}:{proof.get('estimate_stage') or 'monthly'}:{proof['release_date']}"


def storage_id(sid,feature,stage):
    return 'BEA_'+sid+'_'+feature.upper()+'_'+(stage or 'MONTHLY').upper()


def number(text):
    text=text.strip().replace('\u2212','-').replace('\u2013','-')
    if not re.fullmatch(r'[+-]?\d+\.\d',text):raise ValueError('Expected a published rate with one decimal')
    value=Decimal(text)
    if not value.is_finite() or abs(value)>1000:raise ValueError('Invalid BEA rate')
    return str(value)


def entry(sid,feature,value,previous=None,field=''):
    return dict(series_id=sid,feature_name=feature,value=number(value),previous=number(previous) if previous is not None else None,
                precision=1,unit='percent',method='published_rate' if feature!='raw' else 'published_level',field=field,definition=MEASURES[(sid,feature)])


def discover(html,stamp):
    proofs=parse_schedule('bea',html,SCHEDULE,stamp)
    tree=Tree(html)
    for p in proofs:
        if p['release_id'] not in (53,54):continue
        if p['release_id']==54:
            matches=[]
            for row in tree.root.find(lambda n:n.tag=='tr'):
                c=cells(row)
                if len(c)<3 or not c[2].startswith('Personal Income and Outlays, '):continue
                try:period=parsed_date(c[2].split(', ',1)[1])
                except ValueError:continue
                if period==p['reference_period']:
                    matches.extend(urljoin(SCHEDULE,a.attrs['href']) for a in row.find(lambda n:n.tag=='a' and n.attrs.get('href')))
            matches={u for u in matches if official(u)}
            if len(matches)==1:p['report_url']=matches.pop()
        clocks=set()
        for row in tree.root.find(lambda n:n.tag=='tr'):
            c=cells(row)
            if len(c)<3:continue
            # Future rows have their own clock before the report is linked.
            # Bind by explicit date, period and stage, never by a guessed URL.
            try:day=parsed_date(re.sub(r'\s+\d{1,2}:\d{2}.*$','',c[0])+', '+p['release_date'][:4])
            except ValueError:continue
            if day!=p['release_date']:continue
            if p['release_id']==54:
                if not c[2].startswith('Personal Income and Outlays, '):continue
                try:period=parsed_date(c[2].split(', ',1)[1])
                except ValueError:continue
                if period!=p['reference_period']:continue
            else:
                q=re.search(r'([1-4](?:st|nd|rd|th) Quarter \d{4})',c[2]);stage=re.search(r'(Advance|Second|Third|Updated) Estimate',c[2])
                if not q or not stage or parsed_date(q[1])!=p['reference_period'] or stage[1].lower()!=p['estimate_stage']:continue
            clock=re.search(r'\b(\d{1,2}:\d{2})\s*(AM|PM)\b',c[0],re.I)
            if clock:clocks.add(datetime.strptime(clock[1]+' '+clock[2].upper(),'%I:%M %p').strftime('%H:%M:%S'))
        if len(clocks)>1 or (p.get('report_url') and len(clocks)!=1):raise ValueError('BEA schedule publication clock absent/ambiguous')
        if clocks:p.update(release_time=clocks.pop(),source_timezone='America/New_York')
    return [p for p in proofs if p['release_id'] in (53,54)]


def report_identity(html,proof,url,stamp):
    if not official(url):raise ValueError('Not a BEA report URL')
    tree=Tree(html);headings=[' '.join(n.text().split()) for n in tree.root.find(lambda n:n.tag=='h1')]
    if proof['release_id']==53:
        result=parse_bea_result(html,proof,url,stamp)
        title=next(h for h in headings if re.search(r'GDP|Gross Domestic Product',h))
    elif proof['release_id']==54:
        title='Personal Income and Outlays, '+date.fromisoformat(proof['reference_period']).strftime('%B %Y')
        if headings.count(title)!=1:raise ValueError('PIO report month/title not confirmed')
        announced=parse_bea_clock(html,proof,url)
        result=dict(release_id=54,reference_period=proof['reference_period'],release_date=proof['release_date'],estimate_stage=None,announced_at=announced,source_url=url,retrieved_at=stamp,series_ids=['PCEPI','PCEPILFE','PCEC96','DSPIC96','PSAVERT'])
    else:raise ValueError('Unsupported BEA family')
    if not result.get('announced_at'):raise ValueError('Full BEA publication clock required for direct rates')
    return {**result,'title':title,'identity':key(proof)}


def parse_report(html,proof,url,stamp):
    result=report_identity(html,proof,url,stamp);tree=Tree(html)
    paragraphs=[' '.join(n.text().split()) for n in tree.root.find(lambda n:n.tag=='p')]
    tables=tree.root.find(lambda n:n.tag=='table');readings=[];missing=[]
    if proof['release_id']==53:
        candidates=[t for t in tables if 'Real GDP and Related Measures' in t.text() and 'SAAR' in t.text()]
        if len(candidates)!=1:raise ValueError('No unique real GDP SAAR summary table')
        table=candidates[0];headers=[cells(r) for r in table.find(lambda n:n.tag=='tr')]
        expected=date.fromisoformat(proof['reference_period']);quarter=(expected.month-1)//3+1
        if not re.search(r'to\s+'+str(expected.year)+r':Q'+str(quarter)+r'\b',table.text(),re.I):raise ValueError('GDP table quarter not confirmed')
        stage=(proof['estimate_stage'].title()+' Estimate')
        columns=[r for r in headers if stage in r]
        values=[r for r in headers if r and r[0]=='Real GDP']
        if len(columns)!=1 or len(values)!=1:raise ValueError('GDP stage column/row not confirmed')
        index=columns[0].index(stage)
        # Some tables omit the empty corner th; align stage headers to data cells.
        index+=len(values[0])-len(columns[0])
        actual=number(values[0][index])
        first=[p for p in paragraphs if re.match(r'Real gross domestic product\s*\(GDP\)',p)]
        if len(first)!=1:raise ValueError('GDP headline not unique')
        if not re.search(r'in the '+['first','second','third','fourth'][quarter-1]+r' quarter of '+str(expected.year)+r'\b',first[0],re.I):raise ValueError('GDP headline quarter conflict')
        m=re.search(r'(increased|decreased) at an annual rate of ([+-]?\d+\.\d) percent',first[0])
        if not m:raise ValueError('GDP annualized headline absent')
        stated=Decimal(m[2])*(-1 if m[1]=='decreased' else 1)
        if stated!=Decimal(actual):raise ValueError('GDP table/headline conflict')
        prior=__import__('app.analytics.calendar_readings',fromlist=['period_before']).period_before(proof['reference_period'],'quarterly')
        q=(date.fromisoformat(prior).month-1)//3;word=['first','second','third','fourth'][q]
        prev=re.search(r'In the '+word+r' quarter, real GDP (increased|decreased) ([+-]?\d+\.\d) percent',first[0])
        previous=str(Decimal(prev[2])*(-1 if prev[1]=='decreased' else 1)) if prev else None
        readings=[entry('GDPC1','qoq_annualized',actual,previous,'Real GDP and Related Measures / '+stage+'; prior-quarter headline')]
    else:
        candidates=[t for t in tables if 'Personal Income and Related Measures' in t.text() and 'Percent change from preceding month' in t.text()]
        if len(candidates)!=1:raise ValueError('PIO monthly summary table absent/ambiguous')
        rows=[cells(r) for r in candidates[0].find(lambda n:n.tag=='tr')]
        month=date.fromisoformat(proof['reference_period']).month
        prior_month=12 if month==1 else month-1
        headers=[r for r in rows if calendar.month_name[month] in r and calendar.month_name[prior_month] in r]
        if len(headers)!=1:raise ValueError('PIO previous/current month columns not confirmed')
        header=headers[0]
        for label,sid in [('PCE price index','PCEPI'),('PCE price index excluding food and energy','PCEPILFE'),('Real PCE','PCEC96'),('Real DPI','DSPIC96')]:
            matched=[r for r in rows if r and r[0]==label]
            if len(matched)!=1:missing.append(sid+':mom');continue
            r=matched[0];offset=len(r)-len(header)
            readings.append(entry(sid,'mom',r[header.index(calendar.month_name[month])+offset],r[header.index(calendar.month_name[prior_month])+offset],label+' / percent change from preceding month'))
        annual=[p for p in paragraphs if p.startswith('From the same month one year ago, the PCE price index')]
        if len(annual)==1:
            m=re.search(r'Excluding food and energy, the PCE price index (increased|decreased) (\d+\.\d) percent from one year ago',annual[0])
            if m:readings.append(entry('PCEPILFE','yoy',str(Decimal(m[2])*(-1 if m[1]=='decreased' else 1)),field='Core PCE / from the same month one year ago'))
        if not any(r['feature_name']=='yoy' for r in readings):missing.append('PCEPILFE:yoy')
        saving=[p for p in paragraphs if 'personal saving rate' in p.lower() and 'percentage of DPI' in p]
        if len(saving)==1:
            m=re.search(r'personal saving rate.*?was ([+-]?\d+\.\d) percent',saving[0])
            if m:readings.append(entry('PSAVERT','raw',m[1],field='Personal saving rate / percentage of DPI'))
        if not any(r['series_id']=='PSAVERT' for r in readings):missing.append('PSAVERT:raw')
        # Independent monthly price prose must agree if supplied.
        price=[p for p in paragraphs if p.startswith('From the preceding month, the PCE price index')]
        if len(price)>1:raise ValueError('Ambiguous monthly price paragraph')
        if price:
            for sid,pattern in [('PCEPI',r'for \w+ (increased|decreased) (\d+\.\d) percent'),('PCEPILFE',r'Excluding food and energy, the PCE price index (increased|decreased) (\d+\.\d) percent')]:
                m=re.search(pattern,price[0]);row=next((r for r in readings if r['series_id']==sid and r['feature_name']=='mom'),None)
                if m and row and Decimal(row['value'])!=Decimal(m[2])*(-1 if m[1]=='decreased' else 1):raise ValueError('PIO table/text conflict')
    if not readings:raise ValueError('No supported published BEA readings')
    return {**result,'readings':readings,'missing_measures':missing,'precision':1,'source':SOURCE}


def receipts(connection):
    with connection.cursor() as c:
        c.execute('SELECT id,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata FROM publisher_documents WHERE source=%s ORDER BY retrieved_at,id',(SOURCE,))
        return [dict(zip(('id','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata'),r)) for r in c.fetchall()]


def store_report(connection,proof,metadata,now):
    docs=[d for d in receipts(connection) if d['kind']==metadata['identity']]
    if docs and proof['raw_hash']!=docs[-1]['raw_hash'] and any(d['raw_hash']==proof['raw_hash'] for d in docs):raise ValueError('Known older BEA document replayed')
    if docs and proof['raw_hash']==docs[-1]['raw_hash']:return str(docs[-1]['id']),0
    revisions=[]
    for row in metadata['readings']:
        old=next((r for d in reversed(docs) for r in d['metadata']['readings'] if r['series_id']==row['series_id'] and r['feature_name']==row['feature_name']),None)
        if old and (old['value'],old['previous'])!=(row['value'],row['previous']):revisions.append(dict(measure=row['series_id']+':'+row['feature_name'],before=old,after=row,previous_document_id=str(docs[-1]['id'])))
    with connection.cursor() as c:
        c.execute('''INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)''',(proof['id'],SOURCE,metadata['identity'],proof['source_url'],proof['retrieved_at'],proof['http_status'],proof['raw_hash'],proof['raw_path'],json.dumps({**metadata,'revisions':revisions},default=str)))
        for row in metadata['readings']:
            sid=storage_id(row['series_id'],row['feature_name'],metadata['estimate_stage'])
            c.execute("INSERT INTO series(series_id,name,short_name,category,frequency,unit) VALUES (%s,%s,%s,'bea_direct',%s,'percent') ON CONFLICT(series_id) DO NOTHING",(sid,row['definition'],row['definition'],'quarterly' if metadata['release_id']==53 else 'monthly'))
            c.execute('''INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source,source_document_id,publication_document_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(series_id,observation_date,vintage_date) DO UPDATE SET
                value=EXCLUDED.value,source_document_id=EXCLUDED.source_document_id,publication_document_id=EXCLUDED.publication_document_id,ingested_at=CURRENT_TIMESTAMP WHERE observation_vintages.source=%s''',
                (sid,metadata['reference_period'],now.date(),Decimal(row['value']),SOURCE,proof['id'],proof['id'],SOURCE))
    return proof['id'],len(metadata['readings'])


def backoff_from_error(error,now):
    if not isinstance(error,httpx.HTTPStatusError):return None
    response=error.response;header=response.headers.get('Retry-After')
    if response.status_code not in (429,503):return None
    if header:
        try:
            seconds=int(header)
            if seconds<0:raise ValueError('Negative Retry-After')
            return (now+timedelta(seconds=seconds)).isoformat()
        except (ValueError,OverflowError):
            try:return max(now,parsedate_to_datetime(header).astimezone(timezone.utc)).isoformat()
            except (TypeError,ValueError):pass
    return (now+timedelta(seconds=900)).isoformat() if response.status_code==429 else None


def sync_source(client,connection,now=None,raw_root=None,selected=None,release_aware=False,check_mode='standard'):
    now=now or datetime.now(timezone.utc);captures=[];errors=[];changed=0
    def fetch(url):
        if url!=SCHEDULE and not official(url):raise ValueError('Nonofficial BEA URL')
        before_request('BEA');r=client.get(url)
        if not official(str(r.url)) and str(r.url)!=SCHEDULE:raise ValueError('Nonofficial BEA redirect')
        proof={**capture(r,url,datetime.now(timezone.utc),raw_root or RAW_ROOT),'source':SOURCE};captures.append(proof)
        check['scope']['captures']=captures
        try:r.raise_for_status()
        except httpx.HTTPStatusError as error:
            backoff=backoff_from_error(error,datetime.now(timezone.utc))
            if backoff:
                check['scope']['backoff_until']=backoff
                record_progress(check)
            raise
        return r.text,proof
    scope={'provider':ATTRIBUTION,'check_mode':check_mode,'requested_events':[key(p) for p in selected] if selected is not None else []}
    with availability_check(RESOURCE,scope,connection=connection) as check:
        with connection.transaction():
            html,schedule_proof=fetch(SCHEDULE);proofs=discover(html,schedule_proof['retrieved_at'])
            check['scope']['validated_schedule']=proofs
            due=[p for p in proofs if p['release_date']<=str(now.date()) and p.get('report_url')]
            wanted=selected if selected is not None else [max((p for p in due if p['release_id']==rid),key=lambda p:p['release_date'],default=None) for rid in (53,54)]
            for item in wanted:
                if item is None:errors.append({'reason':'No due BEA document'});continue
                proof=next((p for p in due if key(p)==key(item)),None)
                if not proof:
                    if release_aware:errors.append({'event':key(item),'reason':'Own BEA report not linked for this scheduled event'});continue
                    raise ValueError('Selected BEA event absent from official schedule')
                if release_aware and proof.get('release_time')!=item.get('release_time'):
                    errors.append({'event':key(item),'reason':'Official BEA clock changed'});continue
                try:
                    body,receipt=fetch(proof['report_url']);meta=parse_report(body,proof,proof['report_url'],receipt['retrieved_at'])
                    if datetime.fromisoformat(meta['announced_at'])>now:raise ValueError('BEA embargo is in future')
                    with connection.transaction():
                        _,count=store_report(connection,receipt,{**meta,'schedule_provenance':schedule_proof},now);changed+=count
                    if meta['missing_measures']:errors.append({'source_url':proof['report_url'],'missing_measures':meta['missing_measures']})
                except psycopg.Error:raise
                except Exception as err:
                    errors.append({'source_url':proof['report_url'],'reason':str(err)})
                    backoff=backoff_from_error(err,datetime.now(timezone.utc))
                    if backoff:check['scope']['backoff_until']=backoff;break
            check['scope'].update(captures=captures,errors=errors,changed_observations=changed,report_identities=[key(p) for p in wanted if p])
            check.update(status='partial' if errors else 'success',error_code='bea_report_unconfirmed' if errors else None)
        return dict(status=check['status'],**check['scope'])
