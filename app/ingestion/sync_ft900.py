"""Direct Census/BEA FT900 through existing documents and observation tables."""
import calendar
import io
import json
import math
import posixpath
import re
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import psycopg
from pypdf import PdfReader
from app.ingestion.sync_fomc_calendar import Tree
from app.ingestion.sync_empire_state import capture, previous_month, merge_schedule
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check

SOURCE = 'census_bea_ft900'
SID = 'CENSUS_FT900_TOTAL'
NAME = 'U.S. Trade Balance — Goods and Services'
LABEL = 'Trade Balance — SA'
OFFICIAL_TITLE = 'U.S. International Trade in Goods and Services'
SCHEDULE = 'https://www.census.gov/foreign-trade/schedule.html'
BEA_SCHEDULE = 'https://www.bea.gov/news/schedule/full'
ARCHIVE = 'https://www.census.gov/foreign-trade/Press-Release/ft900_index.html'
CURRENT = 'https://www.census.gov/foreign-trade/Press-Release/current_press_release/index.html'
XLSX = 'https://www.census.gov/foreign-trade/Press-Release/current_press_release/exh1.xlsx'
TERMS = 'https://www.bea.gov/help/faq/147'
ATTRIBUTION = 'Source: U.S. Census Bureau and U.S. Bureau of Economic Analysis.'
MODIFICATIONS = 'MacroLens converts millions to billions of USD and computes signed differences. Current-vintage values may include revisions; negative balances are deficits. No publisher endorsement is implied.'
RAW_ROOT = Path(__file__).resolve().parents[2] / 'data/raw/census_bea_ft900'
NS = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
MONTHS = {m.lower(): i for i,m in enumerate(calendar.month_name) if m}


def normalized(text):
    return ' '.join(text.split())


def identity(period):
    return 'ft900:'+period[:7]+':monthly'


def month(text):
    match = re.fullmatch(r'([A-Za-z]+)(?: and Annual)? (20\d{2})', normalized(text), re.I)
    if not match or match[1].lower() not in MONTHS:
        raise ValueError('Unconfirmed FT900 reference month')
    return str(date(int(match[2]),MONTHS[match[1].lower()],1))


def record(period, day, proof, document_url=None):
    return dict(event_id=identity(period),reference_period=period,release_date=day,
        release_time='08:30:00',source_timezone='America/New_York',date_status='confirmed',time_status='confirmed',
        source_url=proof['source_url'],time_source_url=proof['source_url'],schedule_status='confirmed',
        document_url=document_url,schedule_provenance=proof)


def parse_schedule(content, proof):
    html = content.decode('utf-8')
    section = re.search(r'<h[1-6]\b[^>]*>\s*FT900\s+U\.S\. International Trade in Goods and Services\s*</h[1-6]>(.*?)(?=<h[1-6]\b|$)', html, re.S|re.I)
    if not section:
        raise ValueError('Distinct FT900 schedule section missing')
    tree = Tree(section[1]).root
    if not re.search(r'8:30\s*a\.?m\.?\s*\(Eastern\)',tree.text(),re.I):
        raise ValueError('FT900 Eastern clock not confirmed')
    result={};tbd=[]
    for row in tree.find(lambda n:n.tag=='tr'):
        c=[normalized(n.text()) for n in row.find(lambda n:n.tag in ('td','th'))]
        if len(c)!=3 or c[0]=='Statistical Month' or c[0].startswith('All releases'):continue
        period=month(c[0])
        if c[1].upper()=='TBD':tbd.append(period);continue
        day=str(datetime.strptime(c[1],'%B %d, %Y').date())
        item=record(period,day,proof)
        if period in result and result[period]!=item:raise ValueError('Conflicting FT900 schedule rows')
        result[period]=item
    if not result:raise ValueError('Empty FT900 schedule')
    return dict(events=list(result.values()),tbd_periods=sorted(tbd))


def parse_bea_schedule(content,proof):
    result=[]
    for table in Tree(content.decode('utf-8')).root.find(lambda n:n.tag=='table'):
        year=re.search(r'Year\s+(20\d{2})',normalized(table.text()))
        if not year:continue
        for row in table.find(lambda n:n.tag=='tr'):
            c=[normalized(n.text()) for n in row.find(lambda n:n.tag in ('td','th'))]
            if len(c)<3 or not c[2].startswith(OFFICIAL_TITLE+', '):continue
            if c[2].endswith(', Annual Update'):continue  # no separate annual-update event
            period=month(c[2].split(', ',1)[1])
            if not re.search(r'8:30\s*AM',c[0]):raise ValueError('BEA FT900 clock mismatch')
            day=str(datetime.strptime(re.sub(r'\s+8:30\s*AM.*','',c[0])+', '+year[1],'%B %d, %Y').date())
            result.append(record(period,day,proof))
    if not result:raise ValueError('No BEA FT900 rows')
    return result


def parse_archive(content):
    result={}
    for a in Tree(content.decode('utf-8')).root.find(lambda n:n.tag=='a'):
        url=urljoin(ARCHIVE,a.attrs.get('href',''))
        m=re.fullmatch(r'https://www\.census\.gov/foreign-trade/Press-Release/ft900/ft900_(\d{2})(\d{2})\.pdf',url)
        if m:
            period=str(date(2000+int(m[1]),int(m[2]),1))
            result[period]=url
    if not result:raise ValueError('No official archived FT900 PDF links')
    return result


def parse_report(content,period):
    reader=PdfReader(io.BytesIO(content))
    text=normalized(reader.pages[0].extract_text() or '')
    heading=re.search(r'U\.S\. INTERNATIONAL TRADE IN GOODS AND SERVICES,\s*([A-Z]+ 20\d{2})',text)
    if not heading or month(heading[1])!=period:raise ValueError('Wrong FT900 report/month')
    clock=re.search(r'FOR RELEASE AT 8:30 A[Mm] (EDT|EST), ([A-Z]+), ([A-Z]+ \d{1,2}, 20\d{2})',text)
    if not clock:raise ValueError('No dated FT900 publication clock')
    day=str(datetime.strptime(clock[3].title(),'%B %d, %Y').date())
    inst=datetime.fromisoformat(day+'T08:30:00').replace(tzinfo=ZoneInfo('America/New_York'))
    if inst.tzname()!=clock[1] or inst.strftime('%A').upper()!=clock[2]:raise ValueError('FT900 clock timezone/weekday conflict')
    balance=re.search(r'goods and services (deficit|surplus|balance) was \$([\d,.]+) billion in '+calendar.month_name[date.fromisoformat(period).month],text,re.I)
    if not balance:raise ValueError('No total FT900 balance in own report')
    reported=Decimal(balance[2].replace(',',''))*1000*(-1 if balance[1].lower()=='deficit' else 1)
    digits=len(balance[2].split('.')[1]) if '.' in balance[2] else 0
    tolerance=Decimal(1000)/(Decimal(10)**digits)/2
    return dict(reference_period=period,release_date=day,release_time='08:30:00',reported_balance_millions=str(reported),reported_precision_millions=str(tolerance),validation='own_full_ft900_header_and_total_balance')


def _column(cell):
    text=re.fullmatch(r'([A-Z]+)[1-9]\d*',cell)
    if not text:raise ValueError('Invalid XLSX cell address')
    value=0
    for ch in text[1]:value=value*26+ord(ch)-64
    if value>16384:raise ValueError('XLSX column outside worksheet bounds')
    return value


def _xml(archive,name):
    data=archive.read(name)
    if b'<!DOCTYPE' in data or b'<!ENTITY' in data:raise ValueError('Unsafe XML declaration')
    return ET.fromstring(data)


def _sheets(content):
    if not zipfile.is_zipfile(io.BytesIO(content)):raise ValueError('Not XLSX ZIP')
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)>300 or sum(i.file_size for i in z.infolist())>64*1024*1024:
            raise ValueError('Unsafe XLSX ZIP size/entries')
        if any(i.flag_bits&1 for i in z.infolist()):raise ValueError('Encrypted XLSX')
        workbook=_xml(z,'xl/workbook.xml')
        rels={r.attrib['Id']:r.attrib for r in _xml(z,'xl/_rels/workbook.xml.rels')}
        strings=[]
        if 'xl/sharedStrings.xml' in names:
            strings=[''.join(t.text or '' for t in n.findall('.//s:t',NS)) for n in _xml(z,'xl/sharedStrings.xml').findall('s:si',NS)]
        for sheet in workbook.findall('s:sheets/s:sheet',NS):
            link=rels[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            if link.get('TargetMode')=='External' or not link.get('Type','').endswith('/worksheet'):raise ValueError('External worksheet')
            target=posixpath.normpath(posixpath.join('xl',link['Target'])) if not link['Target'].startswith('/') else link['Target'].lstrip('/')
            if not target.startswith('xl/worksheets/'):raise ValueError('Unexpected worksheet path')
            xml=_xml(z,target);rows={};formulas=set();addresses={}
            for row in xml.findall('s:sheetData/s:row',NS):
                number=int(row.attrib['r']);cells={}
                for c in row.findall('s:c',NS):
                    col=_column(c.attrib['r'])
                    if col in cells:raise ValueError('Duplicate cell')
                    v=c.find('s:v',NS);value=v.text if v is not None else ''
                    kind=c.attrib.get('t')
                    if kind=='s':value=strings[int(value)] if value else ''
                    elif kind=='inlineStr':value=''.join(t.text or '' for t in c.findall('.//s:t',NS))
                    elif kind in ('b','e'):value='INVALID_CELL_TYPE'
                    cells[col]=value or '';addresses[(number,col)]=c.attrib['r']
                    if c.find('s:f',NS) is not None:formulas.add((number,col))
                if number in rows:raise ValueError('Duplicate row')
                rows[number]=cells
            # Resolve merged multi-column headers, never infer numeric cells.
            for merged in xml.findall('s:mergeCells/s:mergeCell',NS):
                first,last=merged.attrib['ref'].split(':');r1=int(re.search(r'\d+',first)[0]);r2=int(re.search(r'\d+',last)[0])
                if r1!=r2:continue
                value=rows.get(r1,{}).get(_column(first),'')
                if value.strip().lower() not in ('balance','exports','imports','period'):continue
                for col in range(_column(first),_column(last)+1):rows.setdefault(r1,{}).setdefault(col,value)
                for col in range(_column(first),_column(last)+1):
                    if not rows[r1][col]:rows[r1][col]=value
            yield sheet.attrib['name'],rows,formulas,addresses


def parse_xlsx(content):
    candidates=[]
    for name,rows,formulas,addresses in _sheets(content):
        text=normalized(' '.join(str(v) for row in rows.values() for v in row.values()))
        if re.search(r'Exhibit\s+1\.\s+U\.S\. International Trade in Goods and Services',text,re.I):
            candidates.append((name,rows,formulas,addresses,text))
    if len(candidates)!=1:raise ValueError('Ambiguous or missing Exhibit 1 worksheet')
    name,rows,formulas,addresses,text=candidates[0]
    if 'not seasonally adjusted' in text.lower() or 'seasonally adjusted' not in text.lower():raise ValueError('Exhibit 1 SA not confirmed')
    if not re.search(r'\bIn millions of dollars\b',text,re.I) or re.search(r'\bIn billions of dollars\b',text,re.I):raise ValueError('Exhibit 1 units not millions')
    if not re.search(r'balance of payments\s*\(BOP\)\s*basis',text,re.I):raise ValueError('Exhibit 1 BOP basis not confirmed')
    headers=[]
    for number,row in rows.items():
        if number>30:continue
        for prior in (number-1,number-2):
            groups=rows.get(prior,{})
            columns={group:[c for c,v in row.items() if v.strip().lower() in ('total','total goods and services') and groups.get(c,'').strip().lower()==group] for group in ('balance','exports','imports')}
            periods=[c for c,v in groups.items() if v.strip().lower()=='period']
            if periods and all(len(c)==1 for c in columns.values()):headers.append((number,periods[0],{k:v[0] for k,v in columns.items()}))
    if len(headers)!=1:raise ValueError('Ambiguous Total Balance/Exports/Imports headers')
    header,labelcol,columns=headers[0];year=None;data={};seen=set();previously_published=False
    for number,row in sorted(rows.items()):
        if number<=header:continue
        label=normalized(row.get(labelcol,''));revised=bool(re.search(r'\(R\)',label,re.I))
        clean=re.sub(r'\s*\(R\)','',label,flags=re.I).strip()
        if re.fullmatch(r'20\d{2}',clean):year=int(clean);continue
        if clean.lower() not in MONTHS:
            if re.fullmatch(r'[A-Za-z]+ data as published last month:',clean,re.I):previously_published=True;continue
            numeric=any(row.get(c,'').strip() for c in columns.values())
            if numeric and year is not None and not re.fullmatch(r'Jan\.\s*-\s*[A-Za-z]+\.?',clean,re.I):
                if not(clean=='' and previously_published):raise ValueError('Unrecognized numeric FT900 period row')
                previously_published=False
            continue  # annual/YTD totals and notes are not monthly observations
        if year is None:raise ValueError('Month without explicit year')
        period=str(date(year,MONTHS[clean.lower()],1))
        if period in seen:raise ValueError('Duplicate monthly FT900 row')
        seen.add(period)
        raw={k:normalized(row.get(c,'')) for k,c in columns.items()}
        if any((number,c) in formulas for c in columns.values()):raise ValueError('Formula in FT900 numeric input')
        if not any(raw.values()):continue  # printed future months are not observations
        values={}
        for key,value in raw.items():
            revised=revised or bool(re.search(r'\(R\)',value,re.I))
            value=re.sub(r'\s*\(R\)','',value,flags=re.I).strip().replace('\u2212','-')
            if not re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',value):raise ValueError('Empty or invalid total numeric cell')
            try:numeric=Decimal(value.replace(',',''))
            except InvalidOperation:raise ValueError('Invalid FT900 number')
            if not numeric.is_finite() or not math.isfinite(float(numeric)) or (key!='balance' and numeric<0):raise ValueError('Invalid total exports/imports')
            values[key]=numeric
        if abs(values['exports']-values['imports']-values['balance'])>Decimal('1.5'):raise ValueError('FT900 total arithmetic conflict')
        data[period]={**{k:str(v) for k,v in values.items()},'revised':revised,'cells':{k:addresses.get((number,c),'') for k,c in columns.items()}}
    if not data:raise ValueError('No monthly Exhibit 1 totals')
    if any(min(data)<=period<max(data) and period not in data for period in seen):raise ValueError('Empty historical FT900 row within reported data')
    return dict(sheet=name,source_unit='Millions of Dollars',seasonal_adjustment='Seasonally Adjusted',basis='Balance of Payments',exhibit='Exhibit 1',values=dict(sorted(data.items())),latest_period=max(data))


def receipts(connection):
    with connection.cursor() as c:
        c.execute('SELECT id,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata FROM publisher_documents WHERE source=%s ORDER BY retrieved_at,id',(SOURCE,))
        return [dict(zip(('id','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata'),r)) for r in c.fetchall()]


def store_receipt(connection,kind,proof,metadata):
    with connection.cursor() as c:
        c.execute('''INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(source,kind,raw_hash) DO NOTHING RETURNING id''',
            (proof['id'],SOURCE,kind,proof['source_url'],proof['retrieved_at'],proof['http_status'],proof['raw_hash'],proof['raw_path'],json.dumps(metadata,default=str)))
        found=c.fetchone()
        if found:return str(found[0])
        c.execute('SELECT id FROM publisher_documents WHERE source=%s AND kind=%s AND raw_hash=%s',(SOURCE,kind,proof['raw_hash']))
        return str(c.fetchone()[0])


def read_schedule(connection=None):
    from app.database.connection import get_connection
    owned=connection is None;connection=connection or get_connection()
    try:
        docs=[d for d in receipts(connection) if d['kind'].startswith('schedule:')]
        return docs[-1]['metadata'] if docs else dict(events=[],history=[],tbd_periods=[])
    finally:
        if owned:connection.close()


def load_observations(connection):
    with connection.cursor() as c:
        c.execute('''SELECT DISTINCT ON(observation_date) observation_date,value,vintage_date,source_document_id,publication_document_id
            FROM observation_vintages WHERE series_id=%s AND source=%s ORDER BY observation_date,vintage_date DESC,id DESC''',(SID,SOURCE))
        return {str(day):dict(value=str(value),vintage_date=str(vintage),document_id=str(doc),publication_document_id=str(pub) if pub else None) for day,value,vintage,doc,pub in c.fetchall()}


def sync_source(client,connection,now=None,raw_root=None,history_periods=(),clock=None):
    now=now or datetime.now(timezone.utc);errors=[];captures=[];changed=0;revisions=[];schedule_ok=False;report_ok=False;xlsx_ok=False;pending=True
    def fetch(url):
        p=urlparse(url)
        if p.scheme!='https' or p.hostname not in ('www.census.gov','www.bea.gov'):raise ValueError('Nonofficial FT900 URL')
        before_request('Census/BEA FT900');response=client.get(url)
        actual=urlparse(str(response.url))
        if actual.scheme!='https' or actual.hostname not in ('www.census.gov','www.bea.gov'):raise ValueError('Nonofficial FT900 redirect')
        proof={**capture(response,url,clock() if clock else datetime.now(timezone.utc),raw_root or RAW_ROOT),'source':SOURCE}
        captures.append(proof);response.raise_for_status();return response.content,proof
    def old_replay(docs,kind,proof,period=None):
        known=[d for d in docs if (d['kind']==kind or kind=='schedule' and d['kind'].startswith('schedule:')) and (period is None or d['metadata'].get('reference_period')==period)]
        if known and proof['raw_hash']!=known[-1]['raw_hash'] and any(d['raw_hash']==proof['raw_hash'] for d in known):raise ValueError('Older FT900 version replayed')
    with connection.transaction(),availability_check('census:ft900',{'provider':ATTRIBUTION,'series_ids':[SID]},connection=connection) as check:
        with connection.transaction():
            docs=receipts(connection);old=load_observations(connection);schedule=read_schedule(connection)
            reports={d['metadata']['reference_period']:d for d in docs if d['kind']=='report'}
            pending_rows=[]
            try:
                body,schedule_proof=fetch(SCHEDULE);parsed=parse_schedule(body,schedule_proof);old_replay(docs,'schedule',schedule_proof)
                body,bea_proof=fetch(BEA_SCHEDULE);bea=parse_bea_schedule(body,bea_proof)
                prior_schedules=[d for d in docs if d['kind'].startswith('schedule:')]
                prior_bea=[d['metadata']['bea_provenance']['raw_hash'] for d in prior_schedules]
                if prior_bea and bea_proof['raw_hash']!=prior_bea[-1] and bea_proof['raw_hash'] in prior_bea:raise ValueError('Older BEA FT900 schedule replayed')
                by_period={r['reference_period']:r for r in bea}
                for row in parsed['events']:
                    prior=by_period.get(row['reference_period'])
                    if prior and prior['release_date']!=row['release_date']:raise ValueError('Census/BEA FT900 schedule conflict')
                    by_period[row['reference_period']]=row
                pending_rows=list(by_period.values());schedule_ok=True
            except psycopg.Error:raise
            except Exception as e:errors.append(dict(stage='schedule',reason=str(e)))
            try:
                body,archive_proof=fetch(ARCHIVE);links=parse_archive(body)
                latest=max(p for p in links if p<=str(now.date().replace(day=1)))
                if reports and latest<max(reports):raise ValueError('Older FT900 archive')
                wanted=set(history_periods)|{latest}
                for period in sorted(wanted):
                    if period not in links:raise ValueError('Required report absent from official archive')
                    if period in reports and period!=latest:continue
                    body,proof=fetch(links[period]);metadata=parse_report(body,period)
                    inst=datetime.fromisoformat(metadata['release_date']+'T08:30:00').replace(tzinfo=ZoneInfo('America/New_York'))
                    if inst>now:raise ValueError('Future FT900 report')
                    old_replay(docs,'report',proof,period)
                    if any(r['reference_period']==period and r['release_date']!=metadata['release_date'] for r in pending_rows):raise ValueError('Report and official schedule disagree')
                    did=store_receipt(connection,'report',proof,{**metadata,'archive_provenance':archive_proof})
                    reports[period]={**proof,'id':did,'metadata':metadata}
                report_ok=True
            except psycopg.Error:raise
            except Exception as e:errors.append(dict(stage='report',reason=str(e)))
            if schedule_ok:
                for period,doc in reports.items():
                    if any(r['reference_period']==period and r['release_date']!=doc['metadata']['release_date'] for r in pending_rows):
                        raise ValueError('Archived FT900 publication and schedule conflict')
                for period,doc in reports.items():
                    if not any(r['reference_period']==period for r in pending_rows):pending_rows.append(record(period,doc['metadata']['release_date'],doc,doc['source_url']))
                for row in pending_rows:
                    doc=reports.get(row['reference_period'])
                    if doc:row['document_url']=doc['source_url']
                merged=merge_schedule(schedule,pending_rows,now.isoformat())
                merged.update(tbd_periods=parsed['tbd_periods'],bea_provenance=bea_proof,retained_from=schedule.get('retained_from') or (previous_month(previous_month(previous_month(max(reports)))) if reports else None))
                # Projection identity incorporates BEA and report links independently
                # of Census's raw hash. raw_hash ALWAYS hashes actual response bytes.
                import hashlib
                version=hashlib.sha256(json.dumps([bea_proof['raw_hash'],[(r['event_id'],r['release_date'],r['release_time'],r.get('document_url')) for r in merged['events']],merged['tbd_periods']],sort_keys=True).encode()).hexdigest()
                merged['projection_version']=version
                store_receipt(connection,'schedule:'+version,schedule_proof,merged);schedule=merged
            try:
                body,proof=fetch(XLSX);book=parse_xlsx(body);old_replay(docs,'xlsx',proof)
                previous_books=[d for d in docs if d['kind']=='xlsx']
                if previous_books and book['latest_period']<previous_books[-1]['metadata']['latest_period']:raise ValueError('Older Exhibit 1 under current URL')
                if not reports:raise ValueError('No verified full FT900 report')
                latest_report=max(reports)
                if book['latest_period']>latest_report:raise ValueError('Exhibit period has no published full FT900 report')
                latest_value=book['values'].get(latest_report)
                pending=latest_value is None
                if latest_value and abs(Decimal(latest_value['balance'])-Decimal(reports[latest_report]['metadata']['reported_balance_millions']))>Decimal(reports[latest_report]['metadata']['reported_precision_millions']):
                    raise ValueError('Current Exhibit 1 conflicts with latest official FT900 report')
                start=schedule.get('retained_from','9999-01-01');events={r['reference_period']:r for r in schedule['events']}
                accepted={p:v for p,v in book['values'].items() if start<=p<=latest_report}
                if any(p not in book['values'] for p in old):raise ValueError('Retained FT900 month missing')
                for p,v in accepted.items():
                    if p in old and Decimal(old[p]['value'])!=Decimal(v['balance']):revisions.append(dict(period=p,before=old[p]['value'],after=v['balance'],previous_document_id=old[p]['document_id']))
                metadata={k:v for k,v in book.items() if k!='values'}
                metadata.update(values=accepted,revisions=revisions,pending_report_period=latest_report if pending else None)
                did=store_receipt(connection,'xlsx',proof,metadata)
                with connection.cursor() as cur:
                    cur.execute("INSERT INTO series(series_id,name,short_name,category,frequency,unit) VALUES (%s,%s,%s,'growth','monthly','Millions of Dollars') ON CONFLICT(series_id) DO NOTHING",(SID,NAME,LABEL))
                    for p,v in accepted.items():
                        doc=reports.get(p);pub=str(doc['id']) if doc else None
                        if p in events and datetime.fromisoformat(events[p]['release_date']+'T08:30:00').replace(tzinfo=ZoneInfo('America/New_York'))>now:continue
                        if p in old and Decimal(old[p]['value'])==Decimal(v['balance']) and old[p]['publication_document_id']==pub:continue
                        cur.execute('''INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source,source_document_id,publication_document_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(series_id,observation_date,vintage_date)
                            DO UPDATE SET value=EXCLUDED.value,source_document_id=EXCLUDED.source_document_id,publication_document_id=EXCLUDED.publication_document_id,ingested_at=CURRENT_TIMESTAMP
                            WHERE observation_vintages.source=%s AND (observation_vintages.value IS DISTINCT FROM EXCLUDED.value OR observation_vintages.publication_document_id IS DISTINCT FROM EXCLUDED.publication_document_id)''',
                            (SID,p,now.date(),Decimal(v['balance']),SOURCE,did,pub,SOURCE));changed+=1
                xlsx_ok=True
            except psycopg.Error:raise
            except Exception as e:errors.append(dict(stage='exhibit1',reason=str(e)))
            latest_due=max((r['reference_period'] for r in schedule['events'] if datetime.fromisoformat(r['release_date']+'T08:30:00').replace(tzinfo=ZoneInfo('America/New_York'))<=now),default=None)
            pending=pending or bool(latest_due and latest_due not in reports)
            scope=dict(schedule_checked=schedule_ok,report_checked=report_ok,exhibit1_validated=xlsx_ok,result_pending=pending,
                confirmed_years=sorted({int(r['release_date'][:4]) for r in schedule['events']}),captures=captures,errors=errors,
                changed_observations=changed,historical_revisions=revisions,latest_report_period=max(reports,default=None))
            check['scope'].update(scope)
            check.update(status='error' if not(schedule_ok or report_ok or xlsx_ok) else 'partial' if errors or pending else 'success',error_code='ft900_source_incomplete' if errors else None)
        return dict(status=check['status'],**scope)
