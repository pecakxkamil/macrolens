"""Offline checks of the V5 boundary; real SQL trials live in the PG validator."""
import json
import pytest
from app.database import forecast_f1_authorization_financial as a
from app import cpi_runtime,bls_employment_runtime

@pytest.mark.parametrize('port,user,database,allowed',[(5432,'macrolens','macrolens',False),(55554,'macrolens_ci','macrolens_forecast_f1_ui_test',True),(55554,'macrolens','macrolens_forecast_f1_ui_test',False),(55554,'macrolens_ci','macrolens',False)])
def test_test_only_boundary(port,user,database,allowed):
 assert a.own_clone(dict(host='127.0.0.1',port=port,user=user,database=database)) is allowed

def test_v5_is_append_only_without_any_data_import_or_ddl():
 assert a.CONDITIONS['version']==5 and a.CONDITIONS['ddl'] is False and a.CONDITIONS['data_import'] is False
 assert a.PREDECESSOR_SHA=='ebfe454621a598db1745690e1d94b0d35227add8916f2823a35f9595280e689c'
 assert len(a.DELIVERY_PATHS)==21 and tuple(sorted(set(a.DELIVERY_PATHS)))==a.DELIVERY_PATHS
 assert not any('forecast_f2' in p or 'data/raw' in p for p in a.DELIVERY_PATHS)

def test_no_implicit_hash_or_target_approval():
 p=dict(target={'host':'localhost','port':5432,'database':'macrolens'},backup={})
 with pytest.raises(ValueError,match='Separate exact target'):a.apply(None,p,'wrong','wrong',{})

@pytest.mark.parametrize('version',[1,2,3,4,6])
def test_foreign_token_versions_stop_before_sql(version):
 with pytest.raises(ValueError,match='Separate V5'):a.authorized(None,dict(version=version,plan_sha256='a',target={},artifacts={}))

@pytest.mark.parametrize('runtime,source_name',[(cpi_runtime,'bls_cpi'),(bls_employment_runtime,'source')])
def test_v5_preserves_existing_listener_path_without_a_new_timer(runtime,source_name,tmp_path,monkeypatch):
 from app.analytics.overview_refresh import coordinator
 monkeypatch.setattr(coordinator,'launch',lambda callback:callback())
 seen=[];source=getattr(runtime,source_name)
 monkeypatch.setattr(source,'run',lambda factory,token,directory:seen.append(token['version']) or dict(status='complete',added=0))
 p=tmp_path/'test-only-token.json';p.write_text(json.dumps(dict(version=5)))
 runtime.tick(p,tmp_path);assert seen==[5] and runtime.STATE['last_result']['status']=='complete'

def test_backend_inventory_has_two_explicit_new_runtime_files():
 from app.database.forecast_f1_authorization_v2 import spec,artifacts
 m=spec();assert len(m['paths'])==163 and len(artifacts())==166
 assert 'app/database/forecast_f1_authorization_financial.py' in m['paths']
 assert 'app/database/install_financial_reviewed.py' in m['paths']
