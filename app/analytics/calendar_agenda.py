"""The existing calendar, enriched from stored results and scoped check metadata."""
from datetime import date,datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from app.analytics import release_calendar
from app.analytics.calendar_readings import load_results
from app.analytics.source_checks import load_source_checks
from app.database.connection import get_independent_connection,shared_connection

MAX_CALENDAR_DAYS=366


def event_resources(events):
    resources={('ism:' if e.get('event_type')=='ism_report' else 'fred:')+s['series_id'] for e in events for s in e['series']}
    if any(str(e.get('event_type','')).startswith('michigan_') for e in events):resources.add('michigan:calendar')
    if any(e.get('event_type')=='ism_report' for e in events):resources.add('ism:calendar')
    return resources


def validate_range(start,end):
    if start>end:raise release_calendar.InvalidCalendarRangeError('start_date must be on or before end_date.')
    if (end-start).days>=MAX_CALENDAR_DAYS:raise release_calendar.InvalidCalendarRangeError('Calendar ranges are limited to 366 days.')


def scoped_check(checks,start,end,events,policy):
    sources=[]
    required={'fred:calendar','fed:calendar'}|event_resources(events)
    if any((e.get('schedule_provenance') and e.get('release_id') is not None) or e.get('release_id') in (50,10,46,11,192,9,13) for e in events):required.add('calendar:periods')
    for original in checks['sources']:
        if original['resource'] not in required:continue
        row=dict(original);scope=row.get('scope',{});state=row['status']
        if row['resource'] in ('fred:calendar','calendar:periods'):
            covered_scope=row.get('coverage_scope') or scope
            if not(covered_scope.get('start_date','9999')<=str(start) and covered_scope.get('end_date','')>=str(end)):
                state='partial';row['scope_error']='selected_range_not_checked'
        if row['resource']=='fed:calendar':
            relevant=[e for e in events if str(e.get('event_type','')).startswith('fomc_')]
            missing=[e['release_date'] for e in relevant if not e.get('release_datetime_utc')]
            errors=[t['release_date'] for t in scope.get('time_checks',[]) if t['fetch_status']=='error' and str(start)<=t['release_date']<=str(end)]
            dates=scope.get('dates',[])
            covered=bool(dates) and min(dates)[:4]<=str(start.year) and max(dates)[:4]>=str(end.year)
            if state=='partial' and row.get('error_code')=='decision_times_unavailable' and not missing and covered and not scope.get('legacy_dates_only'):
                state='success';row['checked_at']=row.get('last_finished_at') or row.get('coverage_checked_at')
            if errors:state='error'
            elif missing or not covered or policy.get('status')!='available':state='partial' if state!='error' else 'error'
            row['missing_times']=missing;row['later_missing_times']=[d for d in scope.get('missing_times',[]) if d>str(end)]
        row['range_status']=state
        row.setdefault('checked_at',row.get('coverage_checked_at'))
        sources.append(row)
    errors=any(s['range_status']=='error' for s in sources)
    complete=required<={s['resource'] for s in sources} and all(s['range_status']=='success' and s.get('checked_at') for s in sources)
    return {'status':'error' if errors else 'complete' if complete else 'partial' if any(s.get('checked_at') for s in sources) else 'not_recorded',
            'checked_at':min((s['checked_at'] for s in sources if s.get('checked_at')),default=None),
            'start_date':str(start),'end_date':str(end),'sources':sources,'required_resources':sorted(required)}


def calendar_agenda(start=None,end=None,now=None,category=None):
    now=now or datetime.now(timezone.utc)
    today=now.astimezone(ZoneInfo('Europe/Warsaw')).date()
    start=start or today-timedelta(days=today.weekday());end=end or start+timedelta(days=6)
    validate_range(start,end)
    connection=get_independent_connection()
    try:
        with connection.transaction(),shared_connection(connection):
            with connection.cursor() as cursor:cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            data=release_calendar.list_calendar_events(start,end,category)
            data['events']=load_results(data['events'],start,end,now,connection)
            resources=event_resources(data['events'])
            if any((e.get('schedule_provenance') and e.get('release_id') is not None) or e.get('release_id') in (50,10,46,11,192,9,13) for e in data['events']):resources.add('calendar:periods')
            checks=load_source_checks(start,resources,end)
            with connection.cursor() as cursor:
                cursor.execute("SELECT publication_id FROM overview_refresh_state WHERE id=1")
                data["data_revision"]=str(cursor.fetchone()[0])
            data['check']=scoped_check(checks,start,end,data['events'],data['policy_calendar'])
    finally:connection.close()
    from app.analytics.overview_refresh import coordinator
    try:
        data['refresh']=coordinator.status();data['automatic_refresh_supported']=True
    except Exception:data['automatic_refresh_supported']=False
    data['max_range_days']=MAX_CALENDAR_DAYS
    return data
