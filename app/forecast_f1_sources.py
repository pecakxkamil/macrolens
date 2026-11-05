"""Reviewed Cleveland HTML adapter, not consensus; no implicit endpoints."""
import hashlib
import html
import json
import re
from datetime import datetime,timezone,date
from pathlib import Path
from urllib.robotparser import RobotFileParser
import httpx
from app import forecast_f1 as f

URL='https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting'
UA='MacroLens-ForecastF1/1.0 (local noncommercial research; daily nowcast capture)'

def text(value):return html.unescape(re.sub('<[^>]*>',' ',value)).strip()

def parse_cleveland(content,now=None):
 now=now or datetime.now(timezone.utc);body=content.decode('utf-8');out=[]
 if 'Inflation Nowcasting' not in body:raise ValueError('Unexpected publisher document')
 tables=re.findall(r'<table\b[^>]*>(.*?)</table>',body,re.S|re.I)
 found=set()
 for table in tables:
  for caption,transform in [('Inflation, month-over-month percent change','mom'),('Inflation, year-over-year percent change','yoy')]:
   if caption not in text(table):continue
   if transform in found:raise ValueError('Ambiguous nowcast table')
   found.add(transform)
   headers=[text(x) for x in re.findall(r'<th\b[^>]*>(.*?)</th>',table,re.S|re.I)]
   if headers!=['Month','CPI','Core CPI','PCE','Core PCE','Updated']:raise ValueError('Changed nowcast columns')
   for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S|re.I):
    cells=[text(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S|re.I)]
    if len(cells)!=6:continue
    period=datetime.strptime(cells[0],'%B %Y').date().replace(day=1)
    month,day=map(int,cells[5].split('/'));updated=date(now.year,month,day)
    if updated>now.date():updated=date(now.year-1,month,day)
    if not 0<=(now.date()-updated).days<=7:raise ValueError('Stale/unconfirmed update date')
    if abs((period.year-now.year)*12+period.month-now.month)>2:raise ValueError('Unexpected nowcast period')
    for sid,value in zip(('CPIAUCSL','CPILFESL','PCEPI','PCEPILFE'),cells[1:5]):
     if not value:continue
     r=dict(kind='model_nowcast',subject=dict(domain='macro',country='US',indicator=sid,period=str(period),transform=transform,adjustment='SA',unit='percent',methodology='publisher_index_change',publication_stage='main'),value=value,low=None,high=None,source_id='cleveland-inflation',source_url=URL,published_at=str(updated)+'T00:00:00Z',publication_precision='date',methodology='Cleveland inflation nowcast; monthly SA nonannualized; YoY computed from SA monthly path',source_sha256=hashlib.sha256(content).hexdigest(),rights='noncommercial_attributed',note='Federal Reserve Bank of Cleveland. Model nowcast, not consensus; local noncommercial use. Updated date only; first local capture is SQL captured_at.')
     f.validate(r);out.append(r)
 if found!={'mom','yoy'} or not out:raise ValueError('Missing nowcast tables')
 return out

def terms_hash(content):
 body=text(content.decode('utf-8'))
 match=re.search(r'Privacy and Terms of Use(.*?)General Reserve Bank Data Privacy Notice',body,re.S)
 if not match or not re.search(r'Use of the Bank.s Content',match.group(1)):raise ValueError('Terms section unavailable')
 return hashlib.sha256(' '.join(match.group(1).split()).encode()).hexdigest()

def fetch_cleveland(directory,transport=None,expected_terms=None):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 with httpx.Client(timeout=25,follow_redirects=False,transport=transport,headers={'User-Agent':UA}) as client:
  robots=client.get('https://www.clevelandfed.org/robots.txt');robots.raise_for_status()
  parser=RobotFileParser();parser.parse(robots.text.splitlines())
  if not parser.can_fetch(UA,URL):raise ValueError('Robots disallow')
  terms_receipt=None
  if expected_terms:
   terms=client.get('https://www.clevelandfed.org/privacy');terms.raise_for_status()
   if len(terms.content)>5*1024*1024 or terms_hash(terms.content)!=expected_terms:raise ValueError('Reviewed terms changed')
   terms_receipt=dict(url=str(terms.url),status=terms.status_code,sha256=hashlib.sha256(terms.content).hexdigest(),section_sha256=expected_terms)
  with client.stream('GET',URL) as response:
   response.raise_for_status()
   if 'text/html' not in response.headers.get('content-type',''):raise ValueError('Unexpected content type')
   content=b''
   for chunk in response.iter_bytes():
    content+=chunk
    if len(content)>5*1024*1024:raise ValueError('Source size limit')
   records=parse_cleveland(content)
   receipt=dict(url=URL,status=response.status_code,sha256=hashlib.sha256(content).hexdigest(),captured_at=datetime.now(timezone.utc).isoformat(),bytes=len(content),terms=terms_receipt,robots_sha256=hashlib.sha256(robots.content).hexdigest())
 (directory/(receipt['sha256']+'.html')).write_bytes(content)
 (directory/(receipt['sha256']+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 return records,receipt
