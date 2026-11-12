"""Scoped read-only references and Actual evidence for the fixed F1 pilot."""
import json
from datetime import date,datetime,timezone
from app import forecast_f1 as f,earnings
from app.analytics import release_calendar
from app.analytics.calendar_readings import load_results
from app.database.connection import shared_connection
from app.database import activate_earnings_financials as financial

START=date(2026,11,1)
END=date(2026,12,31)

def publication_events(c):
 with shared_connection(c):
  macro=release_calendar.list_calendar_events(START,END)['events']
  macro=load_results(macro,START,END,datetime.now(timezone.utc),c)
  # SA model identities remain unchanged; NSA Actual is not SA freeze evidence.
  for event in macro:
   for measure in event.get('measures',[]):
    if measure.get('selected_source')=='bls:cpi' and measure.get('seasonal_adjustment')=='NSA':measure['actual']=None
  equity=earnings.load_events(c)
 return macro,equity

def reference_data(c):
 from app.database.activate_forecast_f1 import REF_TABLES
 macro,_=publication_events(c)
 selected=[]
 for e in macro:
  if e.get('release_id') not in (10,53,54):continue
  identity={k:e.get(k) for k in ('event_id','release_id','release_date','release_datetime_utc','source_timezone','date_precision','estimate_stage','schedule_status')}
  identity['subjects']=[f.macro_subject(m,e) for m in e.get('measures',[]) if m.get('series_id') in f.MACRO]
  identity['series']=[{k:s.get(k) for k in ('series_id','frequency','unit')} for s in e.get('series',[])]
  selected.append(identity)
 return json.loads(json.dumps(dict(earnings_tables=financial.table_snapshots(c,REF_TABLES),macro_events=selected),default=str))
