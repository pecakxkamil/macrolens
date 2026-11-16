"""V6 fail-closed boundaries; no database or production token."""
import copy
import pytest
from app.database import forecast_f1_authorization_bea as a

@pytest.mark.parametrize('version',[1,2,3,4,5,7])
def test_foreign_token_version_rejected_before_sql(version):
 with pytest.raises(ValueError,match='Separate V6'):a.authorized(None,{'version':version})

def test_exact_target_and_hash_confirmation_required():
 with pytest.raises(ValueError,match='Separate exact target'):
  a.apply(None,{'target':{'host':'localhost','port':5432,'database':'macrolens'},'backup':{}},'foreign','0'*64,{})

@pytest.mark.parametrize('host,port,user,db,expected',[
 ('localhost',5432,'macrolens','macrolens',False),
 ('127.0.0.1',55555,'macrolens_ci','macrolens_forecast_f1_ui_test',True),
 ('remote',55555,'macrolens_ci','macrolens_forecast_f1_ui_test',False),
 ('localhost',55555,'macrolens','macrolens_forecast_f1_ui_test',False)])
def test_clone_boundary(host,port,user,db,expected):
 assert a.own_clone(dict(host=host,port=port,user=user,database=db)) is expected

def test_only_bea_guard_revision_with_pinned_v5_chain():
 assert a.CONDITIONS['version']==6 and not a.CONDITIONS['ddl'] and not a.CONDITIONS['data_import']
 assert a.PREDECESSOR_SHA=='9b2265be70c2efc13845ed3c38c7aea1f8481b08c569726aaf4cb736164b51a4'
 assert a.PREDECESSOR_ARTIFACTS_SHA=='386fb5b3c266e6faa90dca2c748a0cef6969e7666b15d272635415e87c904dad'
 assert len(a.DELIVERY_PATHS)==13
 assert not any('forecast_f2' in p or 'data/raw' in p for p in a.DELIVERY_PATHS)

def test_changed_delivery_inventory_rejected_before_file_access():
 with pytest.raises(ValueError,match='Exact reviewed delivery'):a.validate_delivery([])
