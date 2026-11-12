"""Shared durable anonymous BLS budget; caller holds the existing account lease."""
from datetime import timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb

LOCK = 726530033
RESOURCES = ('bls:employment', 'bls:cpi')
LIMIT = 8
INTERVAL = 900


def claim(c, resource, event, now):
    if resource not in RESOURCES:raise ValueError('Unknown BLS participant')
    rows=c.execute("""SELECT attempted_at,scope FROM source_check_runs
        WHERE resource=ANY(%s) AND (attempted_at>%s OR
        (scope->>'retry_at')::timestamptz>%s) ORDER BY attempted_at DESC""",
        (list(RESOURCES),now-timedelta(days=1),now)).fetchall()
    if sum(r[0]>now-timedelta(days=1) for r in rows)>=LIMIT:return None,None,'daily_limit'
    from app.ingestion.bls_employment import instant
    if any(instant(r[1]['retry_at'])>now for r in rows if r[1].get('retry_at')):
        return None,None,'cooldown'
    identifier=uuid4()
    scope=dict(event=event,key=event['release_date']+':'+event['reference_period'],
        retry_at=(now+timedelta(seconds=INTERVAL)).isoformat(),
        phase='claimed_before_http',budget='shared_bls_anonymous_v1')
    c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,status,scope) VALUES(%s,%s,%s,'running',%s)",
              (identifier,resource,now,Jsonb(scope)))
    return identifier,scope,None
