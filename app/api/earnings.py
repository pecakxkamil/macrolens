"""Read-only earnings endpoints; no provider clients or refresh operations."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException
from app import earnings
from app.analytics.calendar_agenda import calendar_agenda, validate_range

router=APIRouter()


@router.get('/api/v1/calendar/events')
def events(start_date: Optional[date]=None,end_date: Optional[date]=None,domains: str='macro',tickers: Optional[str]=None):
    start=start_date or datetime.now(ZoneInfo('Europe/Warsaw')).date()
    end=end_date or start+timedelta(days=6)
    selected=set(domains.split(',')); symbols=set(tickers.split(',')) if tickers else None
    if not selected or not selected <= {'macro','earnings'} or (symbols and not symbols <= {v[1] for v in earnings.PILOTS.values()}):
        raise HTTPException(422,'Unsupported domain or ticker')
    try: validate_range(start,end)
    except ValueError as error: raise HTTPException(422,str(error)) from error
    try:
        macro=calendar_agenda(start,end) if 'macro' in selected else None
        equity=earnings.calendar_events(start,end,symbols) if 'earnings' in selected else None
        return {'events':([{'domain':'macro','event':e} for e in macro['events']] if macro else [])+(equity['events'] if equity else []),
                'undated':equity['undated'] if equity else [],'macro_data_revision':macro.get('data_revision') if macro else None,
                'earnings_data_revision':equity['earnings_data_revision'] if equity else None,
                'assembled_at':datetime.now(timezone.utc),'snapshot_scope':'independent_domain_snapshots'}
    except Exception as error:
        raise HTTPException(503,'Calendar domain unavailable; earnings requires the opt-in E2A schema.') from error


@router.get('/api/v1/earnings/companies')
def companies():
    return [{'company_id':earnings.identity(cik),'cik':cik,'name':v[0],'ticker':v[1]} for cik,v in earnings.PILOTS.items()]


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
