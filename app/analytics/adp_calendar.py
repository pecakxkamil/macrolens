"""ADP monthly NER is numeric, with results deliberately not integrated."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from app.ingestion.sync_adp_calendar import read_schedule, HOME, LISTING, AGREEMENT


def calendar_events(start,end):
    events=[]
    for row in read_schedule()['events']:
        if not str(start)<=row['release_date']<=str(end):continue
        clock=row.get('release_time') if row.get('time_status')=='confirmed' else None
        instant=datetime.fromisoformat(row['release_date']+'T'+clock).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat().replace('+00:00','Z') if clock else None
        events.append(dict(release_id=None,event_id=row['event_id'],event_type='adp_monthly',
            release_name='ADP National Employment Report',release_date=date.fromisoformat(row['release_date']),
            release_time=clock,release_datetime_utc=instant,source_timezone='America/New_York',date_precision='date',
            reference_period=row.get('reference_period'),reference_period_status=row.get('reference_period_status','unconfirmed'),
            publication_stage='monthly',category='labor',importance='high',importance_origin='macrolens_editorial',
            series=[],measures=[],expects_numeric_result=True,actual=None,previous=None,forecast=None,
            consensus_status='not_integrated',result_status='restricted',result_integration_status='publisher_permission_required',
            license_source_url=AGREEMENT,publisher_reports_url=LISTING,source_link=row['schedule_provenance']['source_url'],
            schedule_provenance=row['schedule_provenance'],date_status='confirmed',time_status=row['time_status'],
            schedule_status=row.get('schedule_status','confirmed'),time_source_url=row.get('time_source_url'),
            time_provenance=row.get('time_provenance'),document_url=row.get('document_url'),
            document_status=row.get('document_status','unconfirmed'),document_provenance=row.get('document_provenance'),
            description='Monthly ADP private-sector payroll employment report, independent of BLS payrolls and weekly NER Pulse. Numerical results are not integrated.'))
    return sorted(events,key=lambda e:(e['release_date'],e['event_id']))
