"""Real SQL/API with explicitly synthetic LOCAL cache, no SQL cap migration."""
import copy
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uuid import uuid4
from unittest.mock import patch
import psycopg
from psycopg import sql
from fastapi.testclient import TestClient
from app import earnings as e, earnings_reports as r, earnings_history as h
from app import earnings_market_cap as cap, earnings_market_cap_cache as cache, earnings_market_cap_public as public
from tests.postgres_earnings_report_validation import seed
from tests.postgres_http_guard import no_publisher_http
from tests.test_earnings_market_cap_public import bundle
from app.database.activate_earnings_financials import table_snapshots
from datetime import date


def verify(connect):
    with connect() as c:
        seed(c);r.initialize_isolated(c);r.import_records(c,json.loads(r.DATA.read_text()))
        h.initialize_isolated(c);h.import_records(c,json.loads(h.DATA.read_text()))
        before=table_snapshots(c);c.commit()
        assert len(before)==24 and 'earnings_market_cap_snapshots' not in before
        with patch.object(e,'get_independent_connection',connect),patch.object(cap,'utc_today',lambda:date(2026,11,4)),patch.object(public,'now',lambda:'2026-11-04T16:00:00+00:00'):
            from app.api.main import app
            with TestClient(app) as client:
                url='/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31'
                original=client.get(url);assert original.status_code==200
                cache.CACHE.write_text(json.dumps(bundle()),encoding='utf-8')
                try:
                    response=client.get(url);assert response.status_code==200
                    rows=response.json()['events'];prior=original.json()['events']
                    for a,b in zip(rows,prior):
                        assert {k:v for k,v in a.items() if not k.startswith('market_cap_')}=={k:v for k,v in b.items() if not k.startswith('market_cap_')}
                    selected=[x for x in rows if x['ticker']=='AAPL'];assert len(selected)==1
                    assert selected[0]['market_cap_usd']=='1234567890123.123456789'
                    assert selected[0]['market_cap_provider']=='TGMCharts'
                    assert all(x['market_cap_usd'] is None for x in rows if x['ticker']!='AAPL')
                    detail=client.get('/api/v1/earnings/events/'+selected[0]['event_id'])
                    assert detail.status_code==200 and detail.json()['market_cap_usd']==selected[0]['market_cap_usd']
                    for alias in ['GOOG','GOOGL']:
                        q=client.get(url+'&tickers='+alias);assert q.status_code==200
                        assert len(q.json()['events'])==1 and q.json()['events'][0]['ticker']=='GOOGL'
                    with patch.object(cap,'utc_today',lambda:date(2026,11,11)):
                        assert all(x['market_cap_usd'] is None for x in client.get(url).json()['events'])
                    cache.CACHE.write_text('{partial',encoding='utf-8')
                    assert client.get(url).status_code==200
                finally:cache.CACHE.unlink(missing_ok=True)
        assert table_snapshots(c)==before
    print('Public LOCAL cache SQL/API PASSED: no cap DDL, all 24 tables unchanged, exact Decimal/date/source, no HTTP, aliases, stale/malformed fallback, preserved Current/Previous.')


def main():
    if os.environ.get('DB_NAME')!='macrolens_public_cap_control':raise ValueError('Owned public cap control required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    if params['host']!='127.0.0.1':raise ValueError('Loopback required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=cap.PREFIX+'public_'+uuid4().hex[:10]
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**params,dbname=name))
        finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


if __name__=='__main__':
    with no_publisher_http():main()
