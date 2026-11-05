"""F1 activation gates and shared lifecycle: no external services."""
import copy
import json
from pathlib import Path
import pytest
import httpx
from app import forecast_f1 as f
from app.database import activate_forecast_f1 as a
from app.forecast_f1_sources import fetch_cleveland,terms_hash


def test_exact_seed_and_dispatch_scope():
 rows=a.seed();assert len(rows)==20
 assert sum(r['kind']=='model_nowcast' for r in rows)==16
 assert sum(r['kind']=='issuer_guidance' for r in rows)==4
 assert {r['subject']['period'] for r in rows if r['kind']=='model_nowcast'}==set(a.policy()['periods'])
 assert not a.policy()['consensus'] and not a.policy()['guidance_refresh']
 assert a.CONDITIONS['apply_http'] is False

@pytest.mark.parametrize('target,token',[('wrong','hash'),('localhost:5432/macrolens','old-e2e-approval')])
def test_old_or_wrong_approval_never_reaches_sql(target,token):
 plan=dict(target_label='localhost:5432/macrolens')
 with pytest.raises(ValueError,match='Separate exact'):a.apply(object(),plan,target,token,{})

def test_sql_schema_remains_the_original_three_table_f1():
 ddl=a.DDL.read_text()
 assert ddl.count('CREATE TABLE ')==3
 assert all('CREATE TABLE '+t in ddl for t in f.TABLES)
 assert 'UPDATE earnings_' not in ddl and 'ALTER TABLE' not in ddl


def test_shared_launcher_listener_only_observes_existing_clock_job():
 from app.analytics.overview_refresh import RefreshCoordinator
 launched=[];ticks=[];c=RefreshCoordinator(launch=launched.append)
 remove=c.register_launch_listener('app.earnings_monitor_runtime',lambda:ticks.append(True))
 def macro():pass
 def earnings():pass
 earnings.__module__='app.earnings_monitor_runtime'
 c.launch(macro);assert not ticks
 c.launch(earnings);assert ticks==[True] and len(launched)==2
 remove();c.launch(earnings);assert ticks==[True]


def test_missing_token_never_dispatches_or_connects(monkeypatch,tmp_path):
 from app import forecast_f1_runtime as runtime
 from app.analytics.overview_refresh import coordinator
 monkeypatch.setattr(runtime,'TOKEN',tmp_path/'missing.json')
 monkeypatch.setattr(coordinator,'launch',lambda fn:pytest.fail('No task for absent token'))
 runtime.tick();assert runtime.status()['status']=='awaiting_activation'


def test_terms_change_stops_before_data_download(tmp_path):
 calls=[]
 def response(request):
  calls.append(str(request.url))
  if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nAllow: /')
  return httpx.Response(200,text='Privacy and Terms of Use Use of the BankXs Content changed General Reserve Bank Data Privacy Notice')
 with pytest.raises(ValueError,match='terms changed'):
  fetch_cleveland(tmp_path,httpx.MockTransport(response),'0'*64)
 assert len(calls)==2 and not any('/inflation-nowcasting' in x for x in calls)


def test_terms_hash_ignores_page_shell_and_whitespace():
 a1=b'<h2>Privacy and Terms of Use</h2><h3>Use of the BankXs Content</h3><p>Personal  use only.</p><h2>General Reserve Bank Data Privacy Notice</h2>old footer'
 a2=b'new header Privacy and Terms of Use Use of the BankXs Content Personal use only. General Reserve Bank Data Privacy Notice new footer'
 assert terms_hash(a1)==terms_hash(a2)


def test_frozen_gate_catches_artifacts_and_ledger(monkeypatch):
 plan=dict(version=1,ready_for_apply=True,conditions=a.CONDITIONS,artifacts={},dispatch=a.policy(),ledger={},ddl={})
 with pytest.raises(ValueError,match='Frozen F1'):a.frozen(plan)
