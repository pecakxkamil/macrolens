"""Read-only Michigan calendar, with numerical integration explicitly restricted."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from app.ingestion.sync_michigan_calendar import read_schedule, REPORTS, AGREEMENT


def calendar_events(start, end):
    result = []
    for row in read_schedule()['events']:
        if not str(start) <= row['release_date'] <= str(end):
            continue
        clock = row.get('release_time') if row.get('time_status') == 'confirmed' else None
        instant = datetime.fromisoformat(row['release_date']+'T'+clock).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat().replace('+00:00','Z') if clock else None
        stage = row['stage']
        result.append(dict(release_id=None, event_id=row['event_id'], event_type='michigan_'+stage,
            release_name='Michigan Consumer Sentiment — '+stage.title(), release_date=date.fromisoformat(row['release_date']),
            release_time=clock, release_datetime_utc=instant, source_timezone='America/New_York', date_precision='date',
            reference_period=row['reference_period'], publication_stage=stage, category='consumer',
            importance='high' if stage=='preliminary' else 'medium', importance_origin='macrolens_editorial',
            series=[], measures=[], expects_numeric_result=True, actual=None, previous=None, forecast=None,
            consensus_status='not_integrated', result_integration_status='publisher_permission_required',
            result_status='restricted', license_source_url=AGREEMENT,
            source_link=row['schedule_provenance']['source_url'], date_status='confirmed', time_status=row['time_status'],
            schedule_status=row.get('schedule_status','confirmed'), schedule_provenance=row['schedule_provenance'],
            date_source_url=row.get('date_source_url', row['schedule_provenance']['source_url']),
            date_provenance=row.get('date_provenance', row['schedule_provenance']),
            time_source_url=row.get('time_source_url'), time_provenance=row.get('time_provenance'),
            document_url=row.get('document_url'), document_status=row.get('document_status','unconfirmed'),
            document_kind=row.get('document_kind'), document_provenance=row.get('document_provenance'),
            publisher_reports_url=REPORTS+row['reference_period'][:4],
            description='University of Michigan Surveys of Consumers. Preliminary and final readings refer to the same survey month. Numerical integration requires publisher permission.'))
    return sorted(result, key=lambda event: (event["release_date"], event["event_id"]))
