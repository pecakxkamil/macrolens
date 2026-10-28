"""Small publisher adapters for existing calendar releases; no observation ingestion."""
import io
import json
import re
import uuid
import calendar
import hashlib
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fractions import Fraction
from pathlib import Path

from app.analytics.calendar_evidence import SNAPSHOT, REVIEWED, read_evidence
from app.ingestion.sync_fomc_calendar import Tree
from app.ingestion.request_budget import before_request
from app.source_checks import availability_check
from app.ingestion.bls_schedule import GROUPS as BLS_GROUPS, parse_html as parse_bls_html, sync_sources, select_records

SOURCES = {
 'bls': 'https://www.bls.gov/schedule/{year}/home.htm',
 'bea': 'https://www.bea.gov/news/schedule/full',
 'soc': 'https://www.census.gov/construction/soc/schedule.html',
 'm3': 'https://www.census.gov/manufacturing/m3/release_schedule.html',
 'chicago': 'https://www.chicagofed.org/research/data/data-release-calendar',
 'retail': 'https://www.census.gov/retail/release_schedule.html',
 'g17': 'https://www.federalreserve.gov/releases/g17/default.htm',
}
BLS = {name: (rid, sids) for name, (rid, sids, _) in BLS_GROUPS.items()}
EVIDENCE_ADAPTER_VERSION=6
G17_METHOD='https://www.federalreserve.gov/releases/g17/OMB/2026/OMB_2026.htm'


def parsed_date(text):
    text = text.strip().replace('.', '')
    text = re.sub(r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*','',text)
    for fmt in ('%B %d, %Y','%b %d, %Y','%m/%d/%Y','%B %Y'):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    quarters = re.fullmatch(r'(First|Second|Third|Fourth|[1-4](?:st|nd|rd|th)) Quarter (\d{4})', text, re.I)
    if quarters:
        q = {'first':1,'second':2,'third':3,'fourth':4}.get(quarters[1].lower()) or int(quarters[1][0])
        return date(int(quarters[2]), (q-1)*3+1, 1).isoformat()
    raise ValueError('No unambiguous date or period')


def cells(row):
    return [' '.join(n.text().split()) for n in row.children if getattr(n,'tag',None) in ('td','th')]


def parse_schedule(kind, html, url, retrieved):
    if kind=='bls':
        publication=next((name for name,(_,_,code) in BLS_GROUPS.items() if url.endswith('/'+code+'.htm')),None)
        return parse_bls_html(html,url,retrieved,publication)
    if kind=='retail':return parse_retail_schedule(html,url,retrieved)
    if kind=='g17':return parse_g17_schedule(html,url,retrieved)[0]
    tree = Tree(html)
    records = []
    def add(rid, sids, day, period, stage=None, clock=None):
        try:
            records.append(dict(release_id=rid,series_ids=sids,release_date=parsed_date(day),
                reference_period=parsed_date(period),estimate_stage=stage,source_url=url,
                retrieved_at=retrieved,binding_method='official_schedule'))
            if clock:records[-1].update(release_time=clock,source_timezone='America/New_York')
        except ValueError:
            pass  # Multi-month/delayed releases require explicit separate evidence.
    for table in tree.root.find(lambda n:n.tag=='table'):
        title = ' '.join(table.text().split())
        for row in table.find(lambda n:n.tag=='tr'):
            c = cells(row)
            if kind == 'bea' and len(c)>=3:
                year = re.search(r'Year\s+(\d{4})', title)
                day = re.sub(r'\s+\d{1,2}:\d{2}.*$', '', c[0])+', '+(year[1] if year else '')
                if c[2].startswith('Personal Income and Outlays, '):
                    add(54,['PCEPI','PCEPILFE','DSPIC96','PCEC96','PSAVERT'],day,c[2].split(', ',1)[1])
                elif c[2].startswith(('GDP (','Gross Domestic Product,')):
                    q = re.search(r'([1-4](?:st|nd|rd|th) Quarter \d{4})',c[2])
                    stage = re.search(r'(Advance|Second|Third|Updated) Estimate',c[2])
                    if q and stage:add(53,['GDPC1'],day,q[1],stage[1].lower())
                    if q and stage and records and records[-1]['release_id']==53:
                        links=row.find(lambda n:n.tag=='a' and n.attrs.get('href'))
                        if links:
                            from urllib.parse import urljoin
                            records[-1]['report_url']=urljoin(url,links[0].attrs['href'])
            elif kind == 'soc' and len(c)==3:
                initial_clock='08:30:00' if re.search(r'New Residential Construction\s*-\s*8:30\s*a\.m\.',title,re.I) else None
                add(27,['HOUST','PERMIT'],c[1],c[0],'initial',initial_clock)
                revised_clock='08:00:00' if re.search(r'Revised Building Permits\s*-\s*8:00\s*a\.m\.',title,re.I) else None
                add(27,['PERMIT'],c[2],c[0],'revised_permits',revised_clock)
                sales_clock='10:00:00' if re.search(r'New Residential Sales\s*-\s*10:00\s*a\.m\.',title,re.I) else None
                add(97,['HSN1F'],c[2],c[0],clock=sales_clock)
            elif kind == 'm3' and len(c)==3:
                advance_clock='08:30:00' if re.search(r'8:30\s*a\.m\.',title,re.I) else None
                full_clock='10:00:00' if re.search(r'10:00\s*a\.m\.',title,re.I) else None
                add(95,['DGORDER'],c[1],c[0],'advance',advance_clock)
                add(95,['DGORDER'],c[2],c[0],'full',full_clock)
            elif kind == 'chicago' and len(c)==2:
                if 'National Activity Index (CFNAI)' in title:add(219,['CFNAI'],c[0],c[1])
                elif 'National Financial Conditions Index (NFCI)' in title:add(221,['NFCI'],c[0],c[1])
    if not records:
        raise ValueError('Publisher table not recognized')
    return records


def parse_retail_schedule(html,url,retrieved):
    # The same page also lists MRTS, inventories and e-commerce: RSAFS maps to
    # the advance MARTS table only, never to the older month in the full report.
    nodes=Tree(html).root.find(lambda n:n.tag in ('h2','h3','table'))
    heading='';records=[]
    for node in nodes:
        if node.tag!='table':heading=' '.join(node.text().split());continue
        if heading!='Advance Monthly Retail Trade Report':continue
        if not re.search(r'Release Date at 8:30 am',node.text(),re.I):raise ValueError('Retail clock not recognized')
        for row in node.find(lambda n:n.tag=='tr'):
            c=cells(row)
            if row.find(lambda n:n.tag=='th'):continue
            if len(c)!=2:raise ValueError('Incomplete advance retail row')
            if c[0]=='Data Month':continue
            if 'to be announced' in c[1].lower():continue
            period,day=parsed_date(c[0]),parsed_date(c[1])
            records.append(dict(release_id=9,series_ids=['RSAFS'],release_date=day,reference_period=period,
                release_time='08:30:00',source_timezone='America/New_York',source_url=url,retrieved_at=retrieved,
                binding_method='official_schedule',estimate_stage='advance'))
    if not records:raise ValueError('No advance retail schedule')
    return records


def parse_g17_schedule(html,url,retrieved,method=None):
    tree=Tree(html);text=' '.join(tree.root.text().split())
    if not re.search(r'monthly releases are issued at 9:15 a\.m\.',text,re.I) or not re.search(r'annual revision is issued at noon',text,re.I):
        raise ValueError('G.17 clocks not confirmed')
    method_valid=method is not None and re.search(r'published about 15 days after the reference month ends', ' '.join(Tree(method).root.text().split()),re.I)
    records=[];rules=[]
    for paragraph in tree.root.find(lambda n:n.tag=='p'):
        content=' '.join(paragraph.text().split());year=re.match(r'^(20\d{2}):',content)
        if not year:continue
        # Apply the documented lag only to explicitly scheduled, ordinary
        # mid-month releases in 2026/27. Delays/combined releases need a report.
        found=list(re.finditer(r'('+'|'.join(calendar.month_name[1:])+r')[\s\u00a0\ufffd]+(\d{1,2})([^,.;]*)(?:[,.;]|$)',content))
        if not found:raise ValueError('G.17 dates not recognized')
        dates={};monthly=[];annual_dates=[]
        for item in found:
            day=date(int(year[1]),list(calendar.month_name).index(item[1]),int(item[2]))
            note=item[3].lower();annual='annual revision' in note
            dates[str(day)]='12:00:00' if annual else '09:15:00'
            if annual:annual_dates.append(str(day))
            if not annual:monthly.append((day,note))
        rules.append(dict(id='g17_clock_'+year[1],release_id=13,valid_from=year[1]+'-01-01',valid_through=year[1]+'-12-31',
            dates=dates,annual_revision_dates=annual_dates,source_timezone='America/New_York',source_url=url,retrieved_at=retrieved))
        for day,note in monthly:
            if not method_valid or day.year not in (2026,2027) or not 10<=day.day<=23 or any(w in note for w in ('delay','combined','revision')):
                continue
            if sum(d.month==day.month for d,_ in monthly)!=1:continue
            ordinal=day.year*12+day.month-2;period=str(date(ordinal//12,ordinal%12+1,1))
            records.append(dict(release_id=13,series_ids=['INDPRO','TCU'],release_date=str(day),reference_period=period,
                release_time='09:15:00',source_timezone='America/New_York',source_url=url,retrieved_at=retrieved,
                binding_method='official_g17_monthly_rule',rule_source_url=G17_METHOD,rule_retrieved_at=retrieved,
                rule_valid_from=year[1]+'-01-01',rule_valid_through=year[1]+'-12-31'))
    if not rules:raise ValueError('No G.17 schedule coverage')
    return records,rules


def parse_g17_report(html,url,retrieved):
    tree=Tree(html)
    released=tree.root.find(lambda n:'dates' in n.attrs.get('class','').split() and 'Release Date:' in n.text())
    tables=tree.root.find(lambda n:n.tag=='table' and n.attrs.get('title')=='Industrial Production and Capacity Utilization: Summary')
    paragraphs=tree.root.find(lambda n:n.tag=='p' and n.text().startswith('Industrial production'))
    if not released or not tables or not paragraphs:raise ValueError('G.17 report header missing')
    day=parsed_date(released[0].text().split('Release Date:',1)[1].strip())
    month=re.search(r'\bin ('+'|'.join(calendar.month_name[1:])+r')\b',paragraphs[0].text())
    years={n.text().strip() for n in tables[0].find(lambda n:n.tag=='th') if re.fullmatch(r'20\d{2}',n.text().strip())}
    if month and len(years)>1:
        # At year boundaries the table explicitly associates each month/year
        # through HTML header IDs. Do not derive the year from release date.
        headers={n.attrs['id']:n for n in tables[0].find(lambda n:n.tag=='th' and n.attrs.get('id'))}
        associated=set()
        for cell in tables[0].find(lambda n:n.tag=='td' and n.attrs.get('headers')):
            linked=[headers[k] for k in cell.attrs['headers'].split() if k in headers]
            cell_years={n.text().strip() for n in linked if re.fullmatch(r'20\d{2}',n.text().strip())}
            cell_months={a.attrs.get('title','').lower() for n in linked for a in n.find(lambda n:n.tag=='abbr')}
            cell_months.update(n.text().strip().lower() for n in linked)
            if month[1].lower() in cell_months and len(cell_years)==1:associated.update(cell_years)
        years=associated
    if not month or len(years)!=1:raise ValueError('G.17 report period ambiguous')
    period=str(date(int(next(iter(years))),list(calendar.month_name).index(month[1]),1))
    if period>day:raise ValueError('G.17 period after publication')
    return dict(release_id=13,series_ids=['INDPRO','TCU'],release_date=day,reference_period=period,
        source_url=url,retrieved_at=retrieved,binding_method='official_release',release_time=report_clock(tree.root.text()),source_timezone='America/New_York')


def report_clock(text):
    match=re.search(r'For release at\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',text,re.I)
    if not match:return None
    return f'{int(match[1])%12+(12 if match[3].lower()=="p" else 0):02d}:{int(match[2]):02d}:00'


def parse_retail_report(html,url,retrieved):
    tree=Tree(html);text=' '.join(tree.root.text().split())
    day=re.search(r'FOR IMMEDIATE RELEASE:\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday), (\w+ \d{1,2}, \d{4})',text)
    period=re.search(r'Advance estimates of U\.S\. retail and food services sales for (\w+ \d{4})',text,re.I)
    if not day or not period:raise ValueError('Advance retail report date/period missing')
    return dict(release_id=9,series_ids=['RSAFS'],release_date=parsed_date(day[1]),reference_period=parsed_date(period[1]),
        source_url=url,retrieved_at=retrieved,binding_method='official_release',estimate_stage='advance',release_time=report_clock(text),source_timezone='America/New_York')


def parse_bls_ics(content,url,retrieved):
    """Only explicit reference periods in the documented public calendar feed."""
    content=re.sub(r'\r?\n[ \t]','',content)
    records=[]
    for block in content.split('BEGIN:VEVENT')[1:]:
        fields={}
        for line in block.splitlines():
            if ':' in line:
                key,value=line.split(':',1);fields[key if key.startswith('DTSTART') else key.split(';',1)[0]]=value.replace('\\,',',').replace('\\n',' ')
        starts=next(((k,v) for k,v in fields.items() if k.startswith('DTSTART')),None)
        if not starts:continue
        key,value=starts
        try:
            when=datetime.strptime(value[:8],'%Y%m%d').date()
            if value.endswith('Z'):
                when=datetime.strptime(value,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/New_York')).date()
            elif 'TZID=' in key and 'America/New_York' not in key and 'VALUE=DATE' not in key:
                continue
            summary=fields.get('SUMMARY','')
            for name,(rid,sids) in BLS.items():
                match=re.fullmatch(re.escape(name)+r' (?:for )?(.+)',summary)
                if not match and summary==name:
                    match=re.fullmatch(r'(?:'+re.escape(name)+r' )?for (.+)',fields.get('DESCRIPTION',''))
                if match:
                    clock=None
                    if 'T' in value:
                        instant=datetime.strptime(value.rstrip('Z'),'%Y%m%dT%H%M%S')
                        if value.endswith('Z'):instant=instant.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/New_York'))
                        clock=instant.time().replace(tzinfo=None).isoformat()
                    records.append(dict(release_id=rid,series_ids=sids,release_date=str(when),reference_period=parsed_date(match[1]),release_time=clock,source_timezone='America/New_York',estimate_stage=None,source_url=url,retrieved_at=retrieved,binding_method='official_calendar_feed'))
        except ValueError:continue
    if not records:raise ValueError('No explicit BLS periods in calendar feed')
    return records


def parse_dol_schedule(html,rule,retrieved):
    tree=Tree(html);text=' '.join(tree.root.text().split())
    if not re.search(r'published each week on Thursday.*8:30',text,re.I):raise ValueError('DOL convention not recognized')
    exceptions={}
    for table in tree.root.find(lambda n:n.tag=='table'):
        if 'Release Date' not in table.text() or 'Release Time' not in table.text():continue
        for row in table.find(lambda n:n.tag=='tr'):
            c=cells(row)
            if len(c)!=2:continue
            try:
                day=parsed_date(c[0]);clock=re.search(r'(\d{1,2}:\d{2})\s*(AM|PM)',c[1],re.I)
                if not clock:continue
                if rule['valid_from']<=day<=rule['valid_through']:
                    exceptions[day]=datetime.strptime(clock[1]+' '+clock[2].upper(),'%I:%M %p').time().isoformat()
            except ValueError:continue
    if not exceptions:raise ValueError('DOL exceptions not recognized')
    cancelled=[]
    from datetime import timedelta
    for day in exceptions:
        d=date.fromisoformat(day)
        if d.weekday()==2:cancelled.append(str(d+timedelta(days=1)))
        elif d.weekday()==4:cancelled.append(str(d-timedelta(days=1)))
    return {**rule,'exceptions':exceptions,'cancelled_dates':cancelled,'schedule_retrieved_at':retrieved}


def parse_m3_result(content,stage,url,retrieved):
    """A posted report's header proves its date/stage, not a provider timestamp."""
    from pypdf import PdfReader
    text=' '.join(PdfReader(io.BytesIO(content)).pages[0].extract_text().split())
    header=re.search(r'FOR RELEASE AT (\d{1,2}:\d{2}) (AM|PM) (?:EDT|EST), (?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY), (\w+ \d{1,2}, \d{4})',text,re.I)
    title=r'MONTHLY ADVANCE REPORT ON DURABLE GOODS MANUFACTURERS.? SHIPMENTS,? INVENTORIES,? AND ORDERS' if stage=='advance' else r'MONTHLY FULL REPORT ON MANUFACTURERS.? SHIPMENTS,? INVENTORIES,? AND ORDERS'
    period=re.search(title+r'\s+(\w+ \d{4})',text,re.I)
    if not header or not period or 'durable goods' not in text.lower():raise ValueError('M3 date/stage/measure not confirmed')
    day=parsed_date(header[3].title());month=parsed_date(period[1].title())
    clock=datetime.strptime(header[1]+' '+header[2].upper(),'%I:%M %p').time()
    instant=datetime.combine(date.fromisoformat(day),clock,tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()
    return dict(release_id=95,series_ids=['DGORDER'],release_date=day,reference_period=month,estimate_stage=stage,source_url=url,retrieved_at=retrieved,announced_at=instant)


def parse_bea_result(html,proof,url,retrieved):
    tree=Tree(html)
    headings=[' '.join(n.text().split()) for n in tree.root.find(lambda n:n.tag=='h1')]
    title=next((h for h in headings if re.search(r'GDP|Gross Domestic Product',h)), '')
    quarter=re.search(r'([1-4](?:st|nd|rd|th) Quarter \d{4})',title,re.I)
    stage=re.search(r'(Advance|Second|Third|Updated) Estimate',title,re.I)
    dates={n.attrs['content'][:10] for n in tree.root.find(lambda n:n.tag=='meta' and n.attrs.get('property')=='article:published_time' and n.attrs.get('content'))}
    if not dates:
        dates={n.attrs['datetime'][:10] for n in tree.root.find(lambda n:n.tag=='time' and n.attrs.get('datetime'))}
    if not quarter or not stage or parsed_date(quarter[1])!=proof['reference_period'] or stage[1].lower()!=proof.get('estimate_stage') or dates!={proof['release_date']}:
        raise ValueError('BEA result date/period/stage not confirmed')
    return dict(release_id=53,series_ids=['GDPC1'],release_date=proof['release_date'],reference_period=proof['reference_period'],estimate_stage=stage[1].lower(),source_url=url,retrieved_at=retrieved)


def parse_claims(content, url, retrieved):
    from pypdf import PdfReader
    text = ' '.join(PdfReader(io.BytesIO(content)).pages[0].extract_text().split())
    released = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday), (\w+ \d{1,2}, \d{4})', text)
    if not released:raise ValueError('No claims announcement date')
    day = parsed_date(released[1]);year=day[:4]
    clock_match=re.search(r'(\d{1,2}):(\d{2})\s*(A\.M\.|P\.M\.)',text,re.I)
    clock=None
    if clock_match:
        hour=int(clock_match[1])%12+(12 if clock_match[3].lower()=='p.m.' else 0)
        clock=f'{hour:02d}:{int(clock_match[2]):02d}:00'
    patterns = {'ICSA':r'In the week ending (\w+ \d{1,2}), the advance figure for seasonally adjusted initial claims',
                'CCSA':r'seasonally adjusted insured unemployment during the week ending (\w+ \d{1,2}) was'}
    records=[]
    for sid,pattern in patterns.items():
        match=re.search(pattern,text,re.I)
        if not match:raise ValueError('Claims reference week not recognized')
        period=parsed_date(match[1]+', '+year)
        if period>day:period=parsed_date(match[1]+', '+str(int(year)-1))
        records.append(dict(release_id=180,release_date=day,series_ids=[sid],reference_period=period,
            source_url=url,retrieved_at=retrieved,binding_method='official_release',release_time=clock,source_timezone='America/New_York',
            announced_at=datetime.combine(date.fromisoformat(day),datetime.strptime(clock,'%H:%M:%S').time(),tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat() if clock else None))
    return records


def rate(text):
    parts=text.split('-')
    return float(sum((Fraction(p) for p in parts),Fraction()))


def parse_decision(html, implementation, day, url, implementation_url, retrieved):
    text=' '.join(Tree(html).root.text().split())
    match=re.search(r'target range for the federal funds rate (?:by .*? )?to (\d+(?:-\d/\d)?(?:\.\d+)?) (?:to|and) (\d+(?:-\d/\d)?(?:\.\d+)?) percent',text,re.I)
    if not match:
        match=re.search(r'target range for the federal funds rate at (\d+(?:-\d/\d)?(?:\.\d+)?) (?:to|and) (\d+(?:-\d/\d)?(?:\.\d+)?) percent',text,re.I)
    effective=re.search(r'Effective (\w+ \d{1,2}, \d{4})',Tree(implementation).root.text(),re.I)
    if not match or not effective:raise ValueError('No explicit target range/effective date')
    announcement=re.search(r'For release at (\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.)',text,re.I)
    announced_at=None
    if announcement:
        hour=int(announcement[1])%12+(12 if announcement[3].lower()=='p.m.' else 0)
        announced_at=datetime.fromisoformat(day).replace(hour=hour,minute=int(announcement[2]),tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()
    return dict(release_date=day,announced_at=announced_at,lower=rate(match[1]),upper=rate(match[2]),effective_date=parsed_date(effective[1]),
        source_url=url,implementation_url=implementation_url,retrieved_at=retrieved)


def sync_periods(client, start, end, events, now=None, path=None, source_kinds=None, include_results=True):
    now=now or datetime.now(timezone.utc);stamp=now.isoformat();target=Path(path or SNAPSHOT)
    existing=read_evidence(target);periods=list(existing['periods']);decisions=list(existing['decisions']);results=list(existing['results']);rules=list(existing['rules']);checks=[]
    publisher_history=list(existing['publisher_history'])
    def merge_publisher(new):
        # Reuse identity-based retention: a narrower response cannot delete
        # absent months, and a moved month archives its previous date.
        from app.ingestion.bls_schedule import merge_source, publisher_identity
        data={'periods':periods,'bls_history':publisher_history}
        for url in sorted({r['source_url'] for r in new}):merge_source(data,url,[r for r in new if r['source_url']==url],publisher_identity)
    raw=target.parents[1]/'raw/calendar_periods'/f'{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}'
    raw.mkdir(parents=True,exist_ok=True)
    captures={}
    def fetch(url):
        before_request('publisher');r=client.get(url)
        capture=raw/(str(len(list(raw.iterdir())))+('.pdf' if r.content.startswith(b'%PDF') else '.html'))
        capture.write_bytes(r.content)
        receipt=dict(source_url=url,retrieved_at=stamp,http_status=r.status_code,raw_hash=hashlib.sha256(r.content).hexdigest(),raw_path=str(capture))
        capture.with_suffix(capture.suffix+'.json').write_text(json.dumps(receipt),encoding='utf-8')
        captures[url]=receipt
        r.raise_for_status()
        return r
    with availability_check('calendar:periods',{'start_date':str(start),'end_date':str(end),
            'source_kinds':sorted(source_kinds) if source_kinds is not None else None,
            'schedule_only':not include_results}) as check:
        bls_data={**existing,'periods':periods}
        if source_kinds is None or 'bls' in source_kinds:
            checks.extend(sync_sources(client,bls_data,start,end,now,raw))
        periods=bls_data['periods']
        for kind,template in SOURCES.items():
            if kind=='bls':continue
            if source_kinds is not None and kind not in source_kinds:continue
            for year in (range(start.year,end.year+1) if kind=='bls' else [None]):
                url=template.format(year=year)
                try:
                    document=fetch(url).text
                    if kind=='g17':
                        try:
                            method=fetch(G17_METHOD).text
                            if not re.search(r'published about 15 days after the reference month ends',' '.join(Tree(method).root.text().split()),re.I):raise ValueError('G.17 reference rule missing')
                            checks.append(dict(source_url=G17_METHOD,status='success',checked_at=stamp))
                        except Exception as error:
                            method=None;checks.append(dict(source_url=G17_METHOD,status='error',error_code=type(error).__name__))
                        new,clocks=parse_g17_schedule(document,url,stamp,method)
                        rules=[r for r in rules if r.get('id') not in {c['id'] for c in clocks}]+clocks
                    else:new=parse_schedule(kind,document,url,stamp)
                    for row in new:
                        row.update(raw_hash=captures[url]['raw_hash'],raw_path=captures[url]['raw_path'],
                                   confirmation_type='automatic_publisher_schedule')
                    merge_publisher(new)
                    checks.append(dict(source_url=url,status='success',checked_at=stamp))
                except Exception as error:
                    checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        for rid,url,parser in [(9,'https://www.census.gov/retail/sales.html',parse_retail_report),
                               (13,'https://www.federalreserve.gov/releases/g17/Current/default.htm',parse_g17_report)]:
            if not include_results or not any(e.get('release_id')==rid for e in events):continue
            try:
                receipt=parser(fetch(url).text,url,stamp)
                if not receipt.get('release_time'):
                    clocks={p['release_time'] for p in periods if p['release_id']==rid and p['release_date']==receipt['release_date'] and p['reference_period']==receipt['reference_period'] and p.get('release_time')}
                    if len(clocks)==1:
                        receipt['release_time']=next(iter(clocks))
                        receipt['clock_source_url']=next(p['source_url'] for p in periods if p['release_id']==rid and p['release_date']==receipt['release_date'] and p.get('release_time')==receipt['release_time'])
                merge_publisher([receipt])
                results=[r for r in results if not(r['release_id']==rid and r['release_date']==receipt['release_date'])]+[receipt]
                checks.append(dict(source_url=url,status='success',checked_at=stamp))
            except Exception as error:checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        for stage,url in [('advance','https://www.census.gov/manufacturing/m3/adv/pdf/durgd.pdf'),('full','https://www.census.gov/manufacturing/m3/prel/pdf/s-i-o.pdf')]:
            if not include_results or not any(e.get('release_id')==95 for e in events):continue
            try:
                result=parse_m3_result(fetch(url).content,stage,url,stamp)
                results=[r for r in results if not(r['release_id']==95 and r['release_date']==result['release_date'] and r['estimate_stage']==stage)]+[result]
                checks.append(dict(source_url=url,status='success',checked_at=stamp,release_date=result['release_date'],estimate_stage=stage))
            except Exception as error:checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        for proof in periods:
            if not include_results:continue
            if proof['release_id']!=53 or not proof.get('report_url') or not str(start)<=proof['release_date']<=min(str(end),str(now.date())):continue
            url=proof['report_url']
            # Links are accepted only from the public publisher schedule.
            from urllib.parse import urlparse
            if urlparse(url).hostname not in ('www.bea.gov','bea.gov'):continue
            try:
                result=parse_bea_result(fetch(url).text,proof,url,stamp)
                results=[r for r in results if not(r['release_id']==53 and r['release_date']==result['release_date'])]+[result]
                checks.append(dict(source_url=url,status='success',checked_at=stamp))
            except Exception as error:checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        if (source_kinds is None or 'dol' in source_kinds) and any(e.get('release_id')==180 for e in events):
            base=next((r for r in reversed(read_evidence().get('rules',[])) if r.get('id')=='dol_weekly_claims'),None)
            if base:
                url=base['source_url']
                try:
                    updated=parse_dol_schedule(fetch(url).text,base,stamp)
                    rules=[r for r in rules if r.get('id')!='dol_weekly_claims']+[updated]
                    checks.append(dict(source_url=url,status='success',checked_at=stamp))
                except Exception as error:checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        past_claims=sorted({str(e['release_date']) for e in events if include_results and e.get('release_id')==180 and str(e['release_date'])<=str(now.date())})
        for day in past_claims:
            d=date.fromisoformat(day);url=f'https://oui.doleta.gov/press/{d.year}/{d:%m%d%y}.pdf'
            try:
                new=parse_claims(fetch(url).content,url,stamp)
                periods=[r for r in periods if not(r['release_id']==180 and r['release_date']==day)]+new
                results=[r for r in results if not(r['release_id']==180 and r['release_date']==day)]+new
                checks.append(dict(source_url=url,status='success',checked_at=stamp))
            except Exception as error:
                checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        # Statements, not daily target-bound observations, prove policy decisions.
        from app.analytics.fomc_calendar import read_schedule
        days=sorted(e['release_date'] for e in read_schedule().get('events',[]) if include_results and e.get('event_type')=='fomc_decision' and e['release_date']<=str(now.date()))
        prior=max((d for d in days if d<str(start)),default=None)
        for day in [d for d in days if str(start)<=d<=str(end) or d==prior]:
            url=f'https://www.federalreserve.gov/newsevents/pressreleases/monetary{day.replace("-","")}a.htm'
            implementation=url.replace('a.htm','a1.htm')
            try:
                decision=parse_decision(fetch(url).text,fetch(implementation).text,day,url,implementation,stamp)
                decisions=[r for r in decisions if r['release_date']!=day]+[decision]
                checks.append(dict(source_url=url,status='success',checked_at=stamp))
            except Exception as error:
                checks.append(dict(source_url=url,status='error',error_code=type(error).__name__))
        reviewed=read_evidence(REVIEWED)
        _,conflicts=select_records(reviewed['periods']+periods)
        payload={'version':1,'retrieved_at':stamp,'periods':periods,'decisions':decisions,'results':results,'rules':rules,'checks':checks,
                 'bls_sources':bls_data['bls_sources'],'bls_history':bls_data['bls_history'],'bls_conflicts':conflicts,'publisher_history':publisher_history}
        target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(payload,indent=2),encoding='utf-8');temporary.replace(target)
        check['scope']['sources']=checks
        check['scope']['bls_conflicts']=conflicts
        if any(c['status']=='error' for c in checks):check.update(status='partial',error_code='publisher_source_unavailable')
        elif any(c['resolution']=='unresolved' for c in conflicts):check.update(status='partial',error_code='publisher_schedule_conflict')
        elif source_kinds is not None:check.update(status='partial',error_code='publisher_scope_partial')
    return payload


def import_bls_document(path,source_url,retrieved_at,target=None):
    """Explicit import of a legally obtained official file; never a network check."""
    from urllib.parse import urlparse
    url=urlparse(source_url)
    if url.hostname!='www.bls.gov' or not url.path.startswith('/schedule/'):
        raise ValueError('An official public BLS schedule URL is required')
    stamp=datetime.fromisoformat(retrieved_at)
    if stamp.tzinfo is None:raise ValueError('Original retrieval timestamp must include its timezone')
    text=Path(path).read_text(encoding='utf-8-sig')
    rows=parse_bls_ics(text,source_url,retrieved_at) if 'BEGIN:VCALENDAR' in text else parse_schedule('bls',text,source_url,retrieved_at)
    for row in rows:
        row.update(binding_method='reviewed_official_schedule',retrieval_method='manual_official_document_import')
    target=Path(target or SNAPSHOT);data=read_evidence(target)
    data['periods'].extend(rows)
    data.update(version=1)
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(target)
    return len(rows)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Import a saved official BLS schedule into existing calendar evidence.')
    parser.add_argument('--import-bls-document',required=True)
    parser.add_argument('--source-url',required=True)
    parser.add_argument('--retrieved-at',required=True)
    args=parser.parse_args()
    print(import_bls_document(args.import_bls_document,args.source_url,args.retrieved_at))
