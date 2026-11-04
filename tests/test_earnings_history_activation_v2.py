"""V2 explicit approval gates without any database connection."""
from unittest.mock import Mock
import copy
import pytest
from app.database import activate_earnings_history_v2 as a
from app.database import activate_earnings as b


@pytest.mark.parametrize('label,token',[('wrong','hash'),('db','wrong')])
def test_old_or_wrong_approval_never_touches_database(label,token):
    c=Mock()
    with pytest.raises(ValueError,match='NEW explicit'):a.apply(c,{'target_label':'db'},label,token,{})
    assert not c.mock_calls


@pytest.mark.parametrize('change',[{'version':1},{'ready_for_apply':False},{'conditions':{}},{'artifacts':{}}])
def test_frozen_v2_gate(change):
    p=dict(version=2,target_label='db',ready_for_apply=True,conditions=a.CONDITIONS,artifacts=a.artifacts(),**{})
    p.update(change);c=Mock()
    with pytest.raises(ValueError,match='Frozen V2'):a.apply(c,p,'db',b.digest(p),{})
    assert not c.mock_calls


def test_scoped_contract_and_exact_existing_ledger():
    assert len(a.PROTECTED)==10 and all(t.startswith('earnings_') for t in a.PROTECTED)
    assert a.CONDITIONS['write_tables']==['earnings_historical_reports']
    assert a.CONDITIONS['advisory_lock']==726530020
    assert '726530019' not in str(a.CONDITIONS)
    rows=a.legacy.seed()
    assert len(rows)==23 and sum(len(r['observations']) for r in rows)==45
    assert all(m['metric']=='revenue' for r in rows if r['ticker']=='CRWD' for m in r['observations'])
