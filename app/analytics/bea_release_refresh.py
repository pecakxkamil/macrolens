"""Bounded publication opportunities, persisted under the existing job lock."""
import copy
import hashlib
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from app.ingestion import sync_bea_reports as source
from app.analytics import bea_direct

KEY='bea_release_aware'
SLOTS=(0,120,300,600,1200)
WINDOW=1800


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value,str) else value


def event(proof):
    if proof.get('source_url')!=source.SCHEDULE or proof.get('release_id') not in (53,54):raise ValueError('Unconfirmed BEA schedule')
    if proof.get('source_timezone')!='America/New_York' or not proof.get('release_time'):raise ValueError('Unconfirmed BEA clock')
    datetime.strptime(proof['release_time'],'%H:%M:%S')
    period=datetime.strptime(proof['reference_period'],'%Y-%m-%d').date()
    if period.day!=1 or (proof['release_id']==53 and (period.month not in (1,4,7,10) or proof.get('estimate_stage') not in ('advance','second','third','updated'))):raise ValueError('Invalid BEA period/stage')
    if proof['release_id']==54 and proof.get('estimate_stage') is not None:raise ValueError('Invalid PIO stage')
    at=datetime.fromisoformat(proof['release_date']+'T'+proof['release_time']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
    return {**proof,'scheduled_at':at.isoformat(),'id':'bea:'+source.key(proof)+':'+at.isoformat(),'expires_at':(at+timedelta(seconds=WINDOW)).isoformat()}


def canonical(proofs):
    groups={}
    for proof in proofs:
        try:item=event(proof)
        except (ValueError,KeyError,TypeError):continue
        identity=(item['release_id'],item['reference_period'],item['estimate_stage'])
        groups.setdefault(identity,{})[item['id']]=item
    # Two competing confirmed dates/clocks are not resolved by guessing.
    return sorted([next(iter(rows.values())) for rows in groups.values() if len(rows)==1],key=lambda p:p['scheduled_at'])


def load_context(connection):
    with connection.cursor() as c:
        c.execute("SELECT scope->'validated_schedule' FROM source_check_runs WHERE resource=%s AND scope ? 'validated_schedule' ORDER BY attempted_at DESC,id DESC LIMIT 1",(source.RESOURCE,))
        row=c.fetchone()
        c.execute("SELECT scope->>'backoff_until' FROM source_check_runs WHERE resource=%s AND scope ? 'backoff_until' ORDER BY attempted_at DESC,id DESC LIMIT 1",(source.RESOURCE,))
        backoff=c.fetchone()
    if row:
        proofs=row[0]
    else:
        # R2 receipts predate validated_schedule. Verify their actual retained
        # schedule bytes once per read; no HTTP or guessed future report URL.
        docs=source.receipts(connection);proofs=[]
        for doc in reversed(docs):
            try:
                receipt=doc['metadata']['schedule_provenance'];body=Path(receipt['raw_path']).read_bytes()
                if hashlib.sha256(body).hexdigest()!=receipt['raw_hash']:continue
                proofs=source.discover(body.decode('utf-8'),receipt['retrieved_at']);break
            except (OSError,ValueError,KeyError):continue
    return {'events':canonical(proofs),'data':bea_direct.load_state(connection),'backoff_until':backoff[0] if backoff else None}


def readings(item,data,now):
    rows=[]
    for sid,feature in source.MEASURES:
        if (sid=='GDPC1')!=(item['release_id']==53):continue
        m=dict(series_id=sid,feature_name=feature,frequency='quarterly' if sid=='GDPC1' else 'monthly',reference_period=item['reference_period'],actual=None,previous=None,previous_period=None,previous_kind='previous_period')
        selected=bea_direct.select(m,item,data,now)
        valid=selected.get('selected_source')==source.SOURCE and selected['actual_provenance']['document_published_at']==item['scheduled_at']
        rows.append((sid,feature,selected['actual'] if valid else None,selected.get('previous') if valid else None,selected.get('published_precision') if valid else None))
    return rows


def plan(context,control,now):
    checks=[];due=[];next_times=[]
    backoffs=[instant(value) for value in (control.get('backoff_until'),context.get('backoff_until')) if value]
    backoff=max(backoffs) if backoffs else None
    future=[instant(p['scheduled_at']) for p in context['events'] if instant(p['scheduled_at'])>now]
    upcoming=min(future) if future else None
    for item in context['events']:
        at=instant(item['scheduled_at']);end=instant(item['expires_at'])
        if now>=end+timedelta(days=1) or (at>now and at!=upcoming):continue
        record=control.get('events',{}).get(item['id'],{})
        values=readings(item,context['data'],now)
        confirmed=bool(values) and all(r[2] is not None for r in values)
        attempts=record.get('attempts',0);last=record.get('slot',-1)
        allowed=[at+timedelta(seconds=s) for i,s in enumerate(SLOTS) if i>last]
        next_at=None;status='confirmed' if confirmed else 'waiting'
        if now>=end and not confirmed:status='window_closed'
        elif not confirmed and attempts<len(SLOTS) and allowed:
            ready=[t for t in allowed if t<=now]
            next_at=now if ready else min(allowed)
            if backoff and backoff>next_at:next_at=backoff
            if next_at>=end:next_at=None;status='backoff'
            elif at<=now and next_at<=now:due.append(item);status='due'
            elif at<=now:status='partial' if any(r[2] is not None for r in values) else 'waiting'
        elif not confirmed:status='attempt_limit'
        if next_at:next_times.append(next_at)
        checks.append({k:item[k] for k in ('id','release_id','reference_period','estimate_stage','release_date','scheduled_at','expires_at')}|dict(attempts=attempts,max_attempts=len(SLOTS),status=status,next_check_at=next_at.isoformat() if next_at else None,confirmed_measures=sum(r[2] is not None for r in values),expected_measures=len(values)))
    return dict(due=due,checks=checks,next_check_at=min(next_times) if next_times else None)


def claim(versions,context,now,standard_next,mode):
    versions=copy.deepcopy(versions);control=versions.setdefault(KEY,{'events':{}})
    if context.get('backoff_until'):
        control['backoff_until']=max(context['backoff_until'],control.get('backoff_until') or context['backoff_until'])
    control['standard_next_at']=standard_next.isoformat();control['mode']=mode
    decision=plan(context,control,now)
    for item in decision['due']:
        slot=max(i for i,s in enumerate(SLOTS) if instant(item['scheduled_at'])+timedelta(seconds=s)<=now)
        old=control.setdefault('events',{}).get(item['id'],{})
        control['events'][item['id']]={'attempts':old.get('attempts',0)+1,'slot':slot,'attempted_at':now.isoformat()}
    if mode=='bea_release_aware':selected=decision['due']
    else:
        selected=[] if context['events'] else None
        for rid in (53,54):
            latest=max((p for p in context['events'] if p['release_id']==rid and instant(p['scheduled_at'])<=now),key=lambda p:p['scheduled_at'],default=None)
            if latest and (now>=instant(latest['expires_at']) or latest in decision['due']):selected.append(latest)
        if control.get('backoff_until') and instant(control['backoff_until'])>now:selected=[]
    versions['_bea_selection']=selected
    return versions


def standard_deadline(state,interval,retry,now):
    control=state.get('source_versions',{}).get(KEY,{})
    if control.get('standard_next_at'):return instant(control['standard_next_at'])
    earliest=instant(state.get('next_check_at'))
    if state.get('completed_at'):
        configured=instant(state['completed_at'])+timedelta(seconds=retry if state['status']=='error' else interval)
        earliest=max(earliest,configured) if earliest else configured
    return earliest or now


def finish(versions,mode,finished,interval,retry,failed=False):
    versions=copy.deepcopy(versions);versions.pop('_bea_selection',None)
    if KEY in versions and mode=='standard':versions[KEY]['standard_next_at']=(finished+timedelta(seconds=retry if failed else interval)).isoformat()
    return versions


def decorate(state,context,now,interval,retry,busy=False):
    state=copy.deepcopy(state);standard=standard_deadline(state,interval,retry,now)
    control=state.get('source_versions',{}).get(KEY,{})
    decision=plan(context,control,now)
    next_at=min(standard,decision['next_check_at']) if decision['next_check_at'] else standard
    if busy and next_at<=now:next_at=now+timedelta(seconds=30)
    elif state['status']!='running' and next_at<=now:next_at=now+timedelta(seconds=5)
    state.update(next_check_at=next_at,standard_next_check_at=standard,refresh_mode=control.get('mode','standard'),bea_release_checks=decision['checks'])
    return state
