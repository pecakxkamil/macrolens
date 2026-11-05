"""Read-only earnings endpoints; no provider clients or refresh operations."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import re
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException
from app import earnings
from app.analytics.calendar_agenda import calendar_agenda, validate_range

router=APIRouter()


@router.get('/api/v1/forecasts/status')
def forecast_status():
    from app.forecast_f1_runtime import status
    return status()


@router.get('/api/v1/earnings/monitor/status')
def monitor_status():
    from app.earnings_monitor_runtime import status
    return status()



@router.get('/api/v1/calendar/events')
def events(start_date: Optional[date]=None,end_date: Optional[date]=None,domains: str='macro',tickers: Optional[str]=None):
    start=start_date or datetime.now(ZoneInfo('Europe/Warsaw')).date()
    end=end_date or start+timedelta(days=6)
    selected=set(domains.split(',')); symbols=set(tickers.split(',')) if tickers else None
    if not selected or not selected <= {'macro','earnings'} or (symbols and (len(symbols)>100 or any(not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}',s) for s in symbols))):
        raise HTTPException(422,'Unsupported domain or ticker')
    try: validate_range(start,end)
    except ValueError as error: raise HTTPException(422,str(error)) from error
    try:
        macro=calendar_agenda(start,end) if 'macro' in selected else None
        equity=earnings.calendar_events(start,end,symbols) if 'earnings' in selected else None
        if equity and equity['events']:
            from app.forecast_f1 import project_earnings
            project_earnings(equity['events'],factory=earnings.get_independent_connection)
            equity['forecast_snapshot_scope']='independent_read_only_forecast_snapshot'
        return {'events':([{'domain':'macro','event':e} for e in macro['events']] if macro else [])+(equity['events'] if equity else []),
                'undated':equity['undated'] if equity else [],'macro_data_revision':macro.get('data_revision') if macro else None,
                'earnings_data_revision':equity['earnings_data_revision'] if equity else None,
                'assembled_at':datetime.now(timezone.utc),'snapshot_scope':'independent_domain_snapshots',
                'forecast_snapshot_scope':equity.get('forecast_snapshot_scope') if equity else None}
    except Exception as error:
        raise HTTPException(503,'Calendar domain unavailable; earnings requires the opt-in E2A schema.') from error


@router.get('/api/v1/earnings/companies')
def companies():
    try: return earnings.companies()
    except Exception as error: raise HTTPException(503,'Earnings store unavailable') from error


@router.get('/api/v1/earnings/events/{event_id}')
def detail(event_id: str):
    try:
        with earnings.get_independent_connection() as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            rows=earnings.load_events(connection)
    except Exception as error: raise HTTPException(503,'Earnings store unavailable') from error
    result=next((e for e in rows if e['event_id']==event_id),None)
    if result is None: raise HTTPException(404,'Unknown earnings event')
    return result
