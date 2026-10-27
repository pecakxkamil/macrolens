"""Automatic Overview checks using existing ingestion, one PostgreSQL lock and atomic publication."""
import copy
import os
import threading
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi.encoders import jsonable_encoder
from app.database.connection import get_independent_connection, shared_connection
from app.analytics.overview_refresh_store import RefreshStore
from app.analytics.source_checks import FRED_SERIES
from app.analytics.overview_readings import READINGS
from app.analytics import economy_brief, history
from app.analytics.overview_check_scope import scope_overview_checks
from app.source_checks import availability_check
from app.ingestion.request_budget import request_budget, before_request


def utc_now():
    return datetime.now(timezone.utc)


def seconds(name, default, minimum=1):
    return max(minimum, int(os.getenv(name, str(default))))


def public_state(state):
    return jsonable_encoder({key: value for key, value in state.items() if key != 'source_versions'})


def collect_histories(today):
    result = {}
    for _, _, sid, feature, *_ in READINGS:
        key = '2s10s' if feature == 'spread' else f'{sid}:{feature}'
        if feature == 'spread': payload = history.load_yield_curve_2s10s_history(end_date=today)
        elif feature == 'raw': payload = history.load_series_history(sid, end_date=today)
        else: payload = history.load_feature_history(sid, feature, end_date=today)
        result[key] = payload
    for sid in ('DFEDTARL','DFEDTARU'):
        result[f'{sid}:raw'] = history.load_series_history(sid, end_date=today)
    return result


def inventory(connection, series_ids):
    with connection.cursor() as cursor:
        cursor.execute('SELECT series_id, MIN(observation_date), COUNT(*), MAX(ingested_at), MAX(vintage_date) FROM observation_vintages WHERE series_id=ANY(%s) GROUP BY series_id', (list(series_ids),))
        return {sid: {'start': str(start), 'signature': [count, str(ingested), str(vintage)]}
                for sid, start, count, ingested, vintage in cursor.fetchall()}


def refresh_fred(series_id, previous, local, connection, now):
    from app.ingestion.fred import fetch_series_metadata, fetch_series_observations
    from app.ingestion.ingest_series import _ingest_series
    from app.analytics.compute_features import compute_features, _load_series_config
    spec = _load_series_config()[series_id]['transformations']
    with availability_check(f'fred:{series_id}', {'provider':'FRED', 'series_ids':[series_id]}) as check:
        metadata = fetch_series_metadata(series_id)
        changed = (previous.get('last_updated') != metadata['last_updated']
            or previous.get('local_signature') != local.get('signature') or previous.get('transformations') != spec)
        details = {'last_updated':metadata['last_updated'], 'observation_end':metadata.get('observation_end')}
        if changed:
            payload = fetch_series_observations(series_id, observation_start=local.get('start'))
            # Full CURRENT snapshot over the stored history catches older revisions;
            # this is not a vintage/ALFRED backfill and does not extend history backward.
            _ingest_series(series_id, response_data=payload)
            compute_features(series_id, preserve_history=True)
            local = inventory(connection, [series_id]).get(series_id, {})
            details['observations_received'] = len(payload['observations'])
        check['scope'].update(details)
    return {**details, 'local_signature':local.get('signature'), 'transformations':spec,
            'attempted_at':now.isoformat()}, {'resource':f'fred:{series_id}', 'status':'success',
            'outcome':'updated' if changed else 'unchanged', **details}


def _due(previous, now, interval):
    attempted = previous.get('attempted_at')
    return not attempted or now >= datetime.fromisoformat(attempted) + timedelta(seconds=interval)


def publication_results_due(events, evidence, versions, previous, now):
    """Reuse the job cadence for newly due reports, never a separate poller."""
    from app.analytics.calendar_evidence import period_evidence
    attempted=datetime.fromisoformat(previous['attempted_at']) if previous.get('attempted_at') else None
    for event in events:
        if event.get('release_id') not in (9,13,95,53,180):continue
        instant=event.get('release_datetime_utc')
        if not instant:continue
        instant=datetime.fromisoformat(instant.replace('Z','+00:00'))
        if not instant<=now or instant<now-timedelta(days=7):continue
        if attempted is None or attempted<instant:return True
        for series in event['series']:
            sid=series['series_id'];proof=period_evidence(evidence,event['release_id'],str(event['release_date']),sid)
            if not proof:continue
            state=versions.get('fred:'+sid,{})
            posted=(state.get('last_updated') or '')[:10]>=str(event['release_date']) and (state.get('observation_end') or '')>=proof['reference_period']
            receipt=any(r['release_id']==event['release_id'] and r['release_date']==str(event['release_date']) and sid in r['series_ids'] and r['reference_period']==proof['reference_period'] and r.get('estimate_stage')==proof.get('estimate_stage') for r in evidence.get('results',[]))
            if posted and not receipt and _due(previous,now,seconds('OVERVIEW_REFRESH_INTERVAL_SECONDS',900,900)):
                return True
    return False


def refresh_sources(connection, previous, now):
    from app.ingestion.sync_release_calendar import sync_release_calendar
    from app.ingestion.sync_fomc_calendar import sync_schedule
    from app.ingestion import discover_ism, import_ism
    versions, results = copy.deepcopy(previous), []
    requested = previous.get("calendar_requested_window")
    required_series = set(FRED_SERIES)
    if requested:
        from app.database.sync_series import load_series_config
        required_series.update(load_series_config())
    local = inventory(connection, required_series)
    for sid in sorted(required_series):
        resource = f'fred:{sid}'
        try:
            before_request('budget')
            with connection.transaction():
                versions[resource], result = refresh_fred(sid, versions.get(resource, {}), local.get(sid, {}), connection, now)
            results.append(result)
        except Exception as error:
            results.append({'resource':resource,'status':'error','error_code':'refresh_failed'})
            # A deadline or a 429 stops additional FRED calls in this job.
            if isinstance(error, TimeoutError) or 'HTTP 429' in str(error):
                results.extend({'resource':f'fred:{other}','status':'skipped','error_code':'provider_backoff'}
                    for other in sorted(required_series) if f'fred:{other}' not in {r['resource'] for r in results})
                break
    today = now.astimezone(ZoneInfo('Europe/Warsaw')).date()
    slow_interval = seconds('OVERVIEW_CALENDAR_INTERVAL_SECONDS', 21600, 900)
    for resource in ('fred:calendar','fed:calendar'):
        scope_missing = resource == 'fred:calendar' and requested and not (versions.get(resource, {}).get('start_date','9999') <= requested['start_date'] and versions.get(resource, {}).get('end_date','') >= requested['end_date'])
        if not scope_missing and not _due(versions.get(resource, {}), now, slow_interval):
            results.append({'resource':resource,'status':'cached','outcome':'within_provider_interval'})
            continue
        if resource == 'fred:calendar' and any(r.get('error_code') == 'provider_backoff' for r in results):
            results.append({'resource':resource,'status':'skipped','error_code':'provider_backoff'})
            continue
        try:
            before_request('budget')
            with connection.transaction():
                if resource == 'fred:calendar':
                    sync_start, sync_end = today-timedelta(days=31), today+timedelta(days=180)
                    if requested:
                        requested_start, requested_end = date.fromisoformat(requested["start_date"]), date.fromisoformat(requested["end_date"])
                        if requested_start<=sync_end and requested_end>=sync_start:
                            sync_start,sync_end=min(sync_start,requested_start),max(sync_end,requested_end)
                        else:sync_start,sync_end=requested_start,requested_end
                    sync_release_calendar(sync_start, sync_end, required_series)
                    result = {'resource':resource,'status':'success'}
                else:
                    with httpx.Client(timeout=20, follow_redirects=True, headers={'User-Agent':'MacroLens calendar refresh'}) as client:
                        payload = sync_schedule(client)
                    unknown = [e['release_date'] for e in payload['events'] if e['release_date'] >= str(today) and not e['release_time']]
                    result = {'resource':resource,'status':'partial' if unknown else 'success',
                              'missing_times':unknown, 'scope':'meeting dates; explicitly published decision times'}
            versions[resource] = {'attempted_at':now.isoformat(), **({'start_date':str(sync_start),'end_date':str(sync_end)} if resource=='fred:calendar' else {})}
            results.append(result)
        except Exception:
            versions[resource] = {**versions.get(resource, {}), 'attempted_at':now.isoformat()}
            results.append({'resource':resource,'status':'error','error_code':'refresh_failed'})
    if requested:
        resource='calendar:periods'
        prior=versions.get(resource,{})
        from app.ingestion.sync_calendar_periods import sync_periods,EVIDENCE_ADAPTER_VERSION
        from app.analytics.release_calendar import list_calendar_events
        from app.analytics.calendar_evidence import read_evidence
        from app.ingestion.bls_schedule import sources_due
        start,end=date.fromisoformat(requested['start_date']),date.fromisoformat(requested['end_date'])
        events=list_calendar_events(start,end)['events']
        covered=prior.get('start_date','9999')<=requested['start_date'] and prior.get('end_date','')>=requested['end_date']
        evidence=read_evidence()
        result_due=publication_results_due(events,evidence,versions,prior,now)
        if covered and prior.get('adapter_version')==EVIDENCE_ADAPTER_VERSION and not _due(prior,now,slow_interval) and not result_due and not sources_due(evidence,now):
            results.append({'resource':resource,'status':'cached','outcome':'within_provider_interval'})
        else:
            try:
                with httpx.Client(timeout=20,follow_redirects=True) as client:
                    payload=sync_periods(client,start,end,events,now)
                versions[resource]={'attempted_at':now.isoformat(),'adapter_version':EVIDENCE_ADAPTER_VERSION,**requested}
                results.append({'resource':resource,'status':'partial' if any(c['status']=='error' for c in payload['checks']) or any(c['resolution']=='unresolved' for c in payload.get('bls_conflicts',[])) else 'success'})
            except Exception:
                versions[resource]={'attempted_at':now.isoformat(),'adapter_version':EVIDENCE_ADAPTER_VERSION,**requested}
                results.append({'resource':resource,'status':'error','error_code':'refresh_failed'})
    ism_interval = seconds('OVERVIEW_ISM_INTERVAL_SECONDS', 21600, 900)
    kinds = [kind for kind, sid in import_ism.KINDS.items() if _due(versions.get('ism:'+sid, {}), now, ism_interval)]
    listing, listing_failed = None, False
    if kinds:
        try:
            listing = discover_ism.fetch_listing()
        except Exception:
            listing_failed = True
    for kind, sid in import_ism.KINDS.items():
        resource = 'ism:'+sid
        if kind not in kinds:
            results.append({'resource':resource,'status':'cached','outcome':'within_provider_interval'})
            continue
        try:
            with connection.transaction():
                with availability_check(resource, {'provider':'ISM via PR Newswire'}) as check:
                    if listing_failed: raise RuntimeError('Latest ISM listing unavailable.')
                    details = discover_ism.import_discovered(kind, listing[kind])
                    check['scope'].update(details)
            versions[resource] = {'attempted_at':now.isoformat(), **details}
            results.append({'resource':resource,'status':'success',**details})
        except Exception:
            versions[resource] = {**versions.get(resource, {}), 'attempted_at':now.isoformat()}
            results.append({'resource':resource,'status':'error','error_code':'latest_publication_not_verified', 'manual_import_available':True})
    return versions, results


def run_refresh(store, previous, now, interval, retry):
    connection = get_independent_connection()
    try:
        with request_budget(seconds('OVERVIEW_REFRESH_TIMEOUT_SECONDS', 600)), connection.transaction(), shared_connection(connection):
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '60s'")
            versions, results = refresh_sources(connection, previous.get('source_versions', {}), now)
            # Existing loaders share this transaction. A failed source rolls back
            # its raw/feature writes to a savepoint; successful sources publish together.
            brief = economy_brief.build_brief()
            histories = collect_histories(now.astimezone(ZoneInfo('Europe/Warsaw')).date())
            finished = utc_now()
            complete = brief['source_checks']['status'] == 'complete'
            failed = any(r['status'] in ('error','skipped') for r in results)
            status = 'error' if not any(r['status'] in ('success','partial','cached') for r in results) else 'complete' if complete and not failed else 'partial'
            publication_id = store.publish(connection, brief, histories, finished)
            store.update({'status':status, 'completed_at':finished, 'next_check_at':finished+timedelta(seconds=retry if failed else interval),
                          'publication_id':publication_id, 'source_versions':versions, 'results':results}, connection)
    finally:
        connection.close()


class RefreshCoordinator:
    def __init__(self, store=None, runner=run_refresh, clock=utc_now, launch=None):
        self.store = store or RefreshStore()
        self.runner, self.clock = runner, clock
        self.launch = launch or (lambda fn: threading.Thread(target=fn, daemon=True, name='overview-refresh').start())

    def intervals(self):
        interval = seconds('OVERVIEW_REFRESH_INTERVAL_SECONDS', 900)
        return interval, max(interval, seconds('OVERVIEW_REFRESH_RETRY_SECONDS', 900))

    def _interrupted(self, now):
        _, retry = self.intervals()
        self.store.update({'status':'error','completed_at':now,'next_check_at':now+timedelta(seconds=retry),
            'results':[{'resource':'overview','status':'error','error_code':'refresh_interrupted'}]})

    def status(self):
        state = self.store.read()
        if state['status'] == 'running':
            lease = self.store.acquire()
            if lease is not None:
                try: self._interrupted(self.clock())
                finally: self.store.release(lease)
                state = self.store.read()
        return public_state(state)

    def request(self, calendar_start=None, calendar_end=None):
        if calendar_start or calendar_end:
            from app.analytics.calendar_agenda import validate_range
            if not(calendar_start and calendar_end):raise ValueError('Both calendar range dates are required.')
            validate_range(calendar_start,calendar_end)
        lease = self.store.acquire()
        if lease is None: return public_state(self.store.read())
        handed_off = False
        try:
            state, now = self.store.read(), self.clock()
            if calendar_start and state['status'] != 'running':
                versions = {**state.get('source_versions',{}), 'calendar_requested_window': {'start_date':str(calendar_start),'end_date':str(calendar_end)}}
                self.store.update({'source_versions':versions})
                state['source_versions']=versions
            if state['status'] == 'running':
                self._interrupted(now)
                return public_state(self.store.read())
            interval, retry = self.intervals()
            earliest = state.get('next_check_at')
            if state.get('completed_at'):
                configured = state['completed_at'] + timedelta(seconds=retry if state['status']=='error' else interval)
                earliest = max(earliest, configured) if earliest else configured
            if earliest and now < earliest:
                return public_state({**state, 'next_check_at':earliest})
            if self.store.publication() is None:
                initialize_publication(self.store)
            interval, retry = self.intervals()
            self.store.start(str(uuid4()), now, now+timedelta(seconds=interval))
            started = public_state(self.store.read())
            def work():
                try: self.runner(self.store, state, now, interval, retry)
                except Exception:
                    # Keep the previous publication after an atomic failure.
                    self.store.update({'status':'error','completed_at':self.clock(),
                        'next_check_at':self.clock()+timedelta(seconds=retry),
                        'results':[{'resource':'overview','status':'error','error_code':'refresh_failed'}]})
                finally: self.store.release(lease)
            self.launch(work)
            handed_off = True
            return started
        finally:
            if not handed_off: self.store.release(lease)


coordinator = RefreshCoordinator()


def initialize_publication(store):
    connection = get_independent_connection()
    try:
        with connection.transaction(), shared_connection(connection):
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            brief = economy_brief.build_brief()
            now = utc_now()
            publication_id = store.publish(connection, brief, collect_histories(now.astimezone(ZoneInfo('Europe/Warsaw')).date()), now)
        return (publication_id, jsonable_encoder({**brief, 'data_revision':publication_id, 'automatic_refresh_supported':True}))
    finally:
        connection.close()


def read_brief():
    store = coordinator.store
    try:
        cached = store.publication()
    except Exception:
        return scope_overview_checks({**economy_brief.build_brief(), 'automatic_refresh_supported':False})
    if cached is None:
        lease = store.acquire()
        if lease is None:
            # Only first-time local cache assembly may need this brief wait;
            # a remote refresh always has a previously published baseline.
            import time
            for _ in range(60):
                time.sleep(0.05)
                cached = store.publication()
                if cached: break
            if cached is None:
                return scope_overview_checks({**economy_brief.build_brief(), 'automatic_refresh_supported':False})
        else:
            try:
                cached = store.publication() or initialize_publication(store)
            finally:
                store.release(lease)
    result = copy.deepcopy(cached[1])
    result['refresh'] = coordinator.status()
    return scope_overview_checks(result)


def read_chart(publication_id, key, start=None, end=None):
    history._validate_date_range(start, end)
    cached = coordinator.store.publication(publication_id, key)
    if not cached or cached[1] is None: raise KeyError('Overview snapshot expired or chart unavailable; reload Overview.')
    payload = copy.deepcopy(cached[1])
    payload['observations'] = [row for row in payload['observations']
        if (start is None or row['observation_date'] >= str(start)) and (end is None or row['observation_date'] <= str(end))]
    payload.update(data_revision=publication_id, start_date=start, end_date=end)
    return payload


def main():
    import argparse
    import json
    import time
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait', action='store_true')
    args = parser.parse_args()
    read_brief()  # Publish the coherent stored baseline before any remote work.
    state = coordinator.request()
    while args.wait and state['status'] == 'running':
        time.sleep(2)
        state = coordinator.status()
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    main()
